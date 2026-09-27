import asyncio
from dataclasses import replace
from urllib.parse import parse_qs
import httpx
import pytest
from src.core.events import EventBus
from src.core.models import AppError


class Store:
    def __init__(self, value=None): self.value = value
    async def load(self): return self.value
    async def save(self, value): self.value = value
    async def delete(self): self.value = None


def token(expiry=10000):
    from src.adapters.twitch_credentials import TwitchCredentials
    return TwitchCredentials('client', '42', 'alice', 'ACCESS_SECRET', 'REFRESH_SECRET', expiry)


def valid():
    return {'client_id':'client', 'user_id':'42', 'login':'alice', 'scopes':['user:read:chat'], 'expires_in':4000}


def service(handler, store=None, **kwargs):
    from src.adapters.twitch_auth import TwitchAuthService
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return TwitchAuthService('client', store or Store(), http, EventBus('test'), clock=kwargs.pop('clock',lambda:1000), **kwargs)


async def ticks(predicate):
    for _ in range(100):
        if predicate(): return
        await asyncio.sleep(0)
    assert predicate()


async def test_dcf_pending_then_success_only_read_scope_no_secret():
    calls=[]
    async def sleep(n): await asyncio.sleep(0)
    def handler(req):
        body=parse_qs(req.content.decode()); calls.append((req.url.path,body))
        if req.url.path.endswith('/device'):
            assert body == {'client_id':['client'], 'scopes':['user:read:chat']}
            return httpx.Response(200,json={'device_code':'DEVICE_SECRET','user_code':'ABCD','verification_uri':'https://www.twitch.tv/activate','expires_in':300,'interval':5})
        if req.url.path.endswith('/validate'): return httpx.Response(200,json=valid())
        if sum(p.endswith('/token') for p,_ in calls)==1: return httpx.Response(400,json={'message':'authorization_pending'})
        return httpx.Response(200,json={'access_token':'ACCESS_SECRET','refresh_token':'REFRESH_SECRET','expires_in':4000})
    auth=service(handler,sleep=sleep)
    try:
        result=await auth.start()
        assert result['user_code']=='ABCD'
        await ticks(lambda:auth.state()['status']=='connected')
        assert (await auth.credentials()).user_id=='42'
        assert not any('client_secret' in b for _,b in calls)
        assert all(x not in str(auth.state())+str(auth.events.recent()) for x in ['ACCESS_SECRET','REFRESH_SECRET','DEVICE_SECRET','ABCD'])
    finally: await auth.close(); await auth.http.aclose()


@pytest.mark.parametrize('problem', ['access_denied','expired_token'])
async def test_dcf_terminal_error_does_not_store_tokens(problem):
    def handler(req):
        if req.url.path.endswith('/device'): return httpx.Response(200,json={'device_code':'d','user_code':'ABCD','verification_uri':'https://www.twitch.tv/activate','expires_in':300,'interval':1})
        return httpx.Response(400,json={'message':problem})
    async def sleep(n): await asyncio.sleep(0)
    auth=service(handler,sleep=sleep)
    try:
        await auth.start(); await ticks(lambda:auth.state()['status']=='error')
        assert await auth.store.load() is None
    finally: await auth.close(); await auth.http.aclose()


async def test_concurrent_refresh_rotates_once():
    calls=[]
    async def handler(req):
        calls.append(req.url.path)
        await asyncio.sleep(0)
        if req.url.path.endswith('/token'): return httpx.Response(200,json={'access_token':'NEW','refresh_token':'ROTATED','expires_in':4000})
        return httpx.Response(200,json=valid())
    auth=service(handler,Store(token(999)))
    try:
        await auth.restore()
        result=await asyncio.gather(auth.credentials(),auth.credentials())
        assert result[0].refresh_token==result[1].refresh_token=='ROTATED'
        assert calls.count('/oauth2/token')==1
        assert (await auth.store.load()).refresh_token=='ROTATED'
    finally: await auth.close(); await auth.http.aclose()


async def test_ambiguous_refresh_timeout_never_retries():
    calls=[]
    def handler(req): calls.append(req.url.path); raise httpx.ReadTimeout('ACCESS_SECRET')
    auth=service(handler,Store(token(999)))
    try:
        await auth.restore()
        for _ in range(2):
            with pytest.raises(AppError): await auth.credentials()
        assert calls==['/oauth2/token']
        assert auth.state()['status']=='error'
        assert 'ACCESS_SECRET' not in str(auth.state())
        assert await auth.store.load() is None
    finally: await auth.close(); await auth.http.aclose()


@pytest.mark.parametrize('change', [{'client_id':'other'}, {'user_id':'other'}, {'scopes':[]}])
async def test_restore_rejects_wrong_identity_or_scope(change):
    auth=service(lambda req:httpx.Response(200,json={**valid(),**change}),Store(token()))
    try:
        await auth.restore()
        with pytest.raises(AppError): await auth.credentials()
    finally: await auth.close(); await auth.http.aclose()


async def test_hourly_validation_revocation_notifies_and_removes_session():
    now=[1000]; revoked=[False]; seen=[]
    def handler(req): return httpx.Response(401 if revoked[0] else 200,json={} if revoked[0] else valid())
    auth=service(handler,Store(token(100000)),clock=lambda:now[0])
    try:
        await auth.restore(); auth.subscribe_invalidated(lambda:seen.append('stopped'))
        revoked[0]=True; now[0]+=3600
        with pytest.raises(AppError): await auth.credentials()
        assert seen==['stopped']
        assert await auth.store.load() is None
    finally: await auth.close(); await auth.http.aclose()


async def test_logout_during_delayed_store_save_cannot_resurrect_tokens():
    entered=asyncio.Event(); release=asyncio.Event()
    class SlowStore(Store):
        async def save(self,v): entered.set(); await release.wait(); self.value=v
    auth=service(lambda req:httpx.Response(200,json=valid()),SlowStore(token()))
    restore=asyncio.create_task(auth.restore())
    await entered.wait()
    logout=asyncio.create_task(auth.disconnect()); await asyncio.sleep(0)
    release.set(); await asyncio.gather(restore,logout)
    assert await auth.store.load() is None
    assert auth.state()['status']=='disconnected'
    await auth.close(); await auth.http.aclose()


async def test_cancel_pending_preserves_existing_session():
    def handler(req):
        if req.url.path.endswith('/device'): return httpx.Response(200,json={'device_code':'d','user_code':'ABCD','verification_uri':'https://www.twitch.tv/activate','expires_in':300,'interval':5})
        return httpx.Response(200,json=valid())
    auth=service(handler,Store(token()))
    try:
        await auth.restore(); await auth.start(); await auth.cancel()
        assert auth.state()['status']=='connected'
        assert (await auth.credentials()).login=='alice'
    finally: await auth.close(); await auth.http.aclose()


async def test_cancel_during_new_account_save_restores_previous_record():
    entered=asyncio.Event(); release=asyncio.Event()
    class SlowStore(Store):
        async def save(self,v):
            if v.access_token=='NEW': entered.set(); await release.wait()
            self.value=v
    def handler(req):
        if req.url.path.endswith('/device'): return httpx.Response(200,json={'device_code':'d','user_code':'A','verification_uri':'https://www.twitch.tv/activate','expires_in':300,'interval':1})
        if req.url.path.endswith('/token'): return httpx.Response(200,json={'access_token':'NEW','refresh_token':'NEW_R','expires_in':4000})
        return httpx.Response(200,json=valid())
    async def sleep(n): await asyncio.sleep(0)
    auth=service(handler,SlowStore(token()),sleep=sleep)
    await auth.restore(); await auth.start(); await entered.wait()
    cancelling=asyncio.create_task(auth.cancel()); await asyncio.sleep(0); release.set(); await cancelling
    assert (await auth.store.load()).access_token=='ACCESS_SECRET'
    assert (await auth.credentials()).access_token=='ACCESS_SECRET'
    await auth.close(); await auth.http.aclose()


async def test_dcf_slow_down_obeys_larger_interval_and_expires():
    now=[1000]; sleeps=[]; calls=[]
    async def sleep(n): sleeps.append(n); now[0]+=n; await asyncio.sleep(0)
    def handler(req):
        calls.append(req.url.path)
        if req.url.path.endswith('/device'): return httpx.Response(200,json={'device_code':'d','user_code':'A','verification_uri':'https://www.twitch.tv/activate','expires_in':12,'interval':2})
        return httpx.Response(400,json={'message':'slow_down'})
    auth=service(handler,clock=lambda:now[0],sleep=sleep)
    try:
        await auth.start(); await ticks(lambda:auth.state()['status']=='error')
        assert sleeps==[2,7,12]
        assert calls.count('/oauth2/token')==2
        assert await auth.store.load() is None
    finally: await auth.close(); await auth.http.aclose()


async def test_second_panel_invalidates_first_device_request():
    entered=asyncio.Event(); release=asyncio.Event(); count=[0]
    async def handler(req):
        count[0]+=1; n=count[0]
        if n==1: entered.set(); await release.wait()
        return httpx.Response(200,json={'device_code':str(n),'user_code':str(n),'verification_uri':'https://www.twitch.tv/activate','expires_in':300,'interval':5})
    auth=service(handler)
    try:
        first=asyncio.create_task(auth.start()); await entered.wait()
        second=await auth.start(); release.set()
        with pytest.raises(AppError): await first
        assert second['user_code']=='2'
    finally: await auth.close(); await auth.http.aclose()

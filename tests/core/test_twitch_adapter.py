import asyncio
import json
from types import SimpleNamespace
import httpx
import pytest
from src.core.models import AppError


def frame(kind,payload=None,id='e'):
    return {'metadata':{'message_type':kind,'message_id':id},'payload':payload or {}}


def welcome(timeout=10): return frame('session_welcome',{'session':{'id':'session','keepalive_timeout_seconds':timeout}})


def comment(id='m1', envelope='e1', source=None):
    return frame('notification',{'subscription':{'type':'channel.chat.message'},'event':{'broadcaster_user_id':'99','chatter_user_login':'alice','message_id':id,'message':{'text':'left'},'source_broadcaster_user_id':source}},envelope)


class Socket:
    def __init__(self,initial=()):
        self.queue=asyncio.Queue(); self.closed=False
        for item in initial: self.queue.put_nowait(item)
    async def recv(self):
        item=await self.queue.get()
        if isinstance(item,Exception): raise item
        return json.dumps(item)
    async def close(self): self.closed=True


class Auth:
    async def credentials(self): return SimpleNamespace(access_token='secret',client_id='client',user_id='42')


def setup(sockets, *, handler=None):
    from src.adapters.twitch import TwitchAdapter
    calls=[]
    def handle(req):
        calls.append(req)
        if handler: return handler(req)
        if req.method=='GET': return httpx.Response(200,json={'data':[{'id':'99'}]})
        return httpx.Response(202,json={'data':[{'id':'sub'}]})
    http=httpx.AsyncClient(transport=httpx.MockTransport(handle))
    async def connect(url,**kwargs): return sockets.pop(0)
    return TwitchAdapter('channel',Auth(),http,connect), calls


async def drain_until(predicate):
    for _ in range(200):
        if predicate(): return
        await asyncio.sleep(0)
    assert predicate()


async def test_subscribe_then_deliver_once_and_filter_shared_chat():
    ws=Socket([welcome(),comment(),comment(envelope='e2'),comment('m2','e3','other'),frame('session_keepalive'),frame('future_type')])
    adapter,calls=setup([ws]); seen=[]
    async def callback(user,text): seen.append((user,text))
    try:
        child=await adapter.connect(callback)
        await drain_until(lambda:ws.queue.empty())
        await asyncio.sleep(0)
        assert seen==[('alice','left')]
        body=json.loads(calls[1].content)
        assert body=={'type':'channel.chat.message','version':'1','condition':{'broadcaster_user_id':'99','user_id':'42'},'transport':{'method':'websocket','session_id':'session'}}
        assert len(calls)==2  # No live-stream status check.
    finally: await adapter.disconnect(); await adapter.http.aclose()
    assert ws.closed and child.done()


async def test_reconnect_retains_dedupe_and_only_one_subscription():
    old=Socket([welcome(),comment(),frame('session_reconnect',{'session':{'reconnect_url':'wss://eventsub.wss.twitch.tv/ws?reconnect=x'}})])
    new=Socket([welcome(),comment(envelope='new'),comment('m2','e2')])
    adapter,calls=setup([old,new]); seen=[]
    async def callback(*args): seen.append(args)
    try:
        await adapter.connect(callback)
        await drain_until(lambda:len(seen)==2)
        assert seen==[('alice','left'),('alice','left')]
        assert old.closed
        assert sum(r.method=='POST' for r in calls)==1
    finally: await adapter.disconnect(); await adapter.http.aclose()
    assert new.closed


@pytest.mark.parametrize('bad,code',[(frame('revocation',{'subscription':{'status':'authorization_revoked'}}),'twitch_auth_required'),(frame('notification',{'subscription':{'type':'channel.chat.message'},'event':{}}),'twitch_protocol_error'),(RuntimeError('secret'),'connection_lost')])
async def test_terminal_events_stop_child_with_safe_error(bad,code):
    ws=Socket([welcome(),bad]); adapter,_=setup([ws])
    async def callback(*args): raise AssertionError('must not execute')
    try:
        child=await adapter.connect(callback)
        with pytest.raises(AppError) as exc: await asyncio.wait_for(child,1)
        assert exc.value.code==code and 'secret' not in str(exc.value)
    finally: await adapter.disconnect(); await adapter.http.aclose()


@pytest.mark.parametrize('response,code',[(httpx.Response(200,json={'data':[]}),'streamer_not_found'),(httpx.Response(403,json={}), 'twitch_forbidden')])
async def test_channel_and_permission_errors(response,code):
    adapter,_=setup([],handler=lambda req:response)
    try:
        with pytest.raises(AppError) as exc: await adapter.connect(None)
        assert exc.value.code==code
    finally: await adapter.disconnect(); await adapter.http.aclose()


async def test_watchdog_fails_and_stop_cleans_partial_connect():
    ws=Socket([welcome(.01)]); adapter,_=setup([ws])
    try:
        child=await adapter.connect(None)
        with pytest.raises(AppError): await asyncio.wait_for(child,.5)
    finally: await adapter.disconnect(); await adapter.http.aclose()
    waiting=Socket(); adapter,_=setup([waiting])
    task=asyncio.create_task(adapter.connect(None))
    await drain_until(lambda:bool(adapter._sockets))
    task.cancel()
    with pytest.raises(asyncio.CancelledError): await task
    assert waiting.closed
    await adapter.http.aclose()

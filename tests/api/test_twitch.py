import asyncio
import httpx
import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.session import SessionManager
from src.core.config_store import ConfigStore
from src.core.models import AppConfig
from src.core.events import EventBus
from src.core.listener_service import ListenerService
from src.adapters.twitch_auth import TwitchAuthService


@pytest.fixture
def twitch_api(tmp_path):
    class Store:
        value=None
        async def load(self): return self.value
        async def save(self,v): self.value=v
        async def delete(self): self.value=None
    class Keys:
        def disable(self): pass
        def enable(self,g): pass
        def submit(self,a): raise AssertionError('unauthorized action')
    static=tmp_path/'static'; static.mkdir(); (static/'index.html').write_text('panel')
    store=ConfigStore(tmp_path/'config.json'); snap=asyncio.run(store.load())
    asyncio.run(store.save(AppConfig(platform='twitch',twitch={'channel':'alice'}),snap.revision))
    bus=EventBus('test'); sessions=SessionManager('test','http://127.0.0.1:8000')
    http=httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'device_code':'DEVICE_SECRET','user_code':'CODE','verification_uri':'https://www.twitch.tv/activate','expires_in':300,'interval':5})))
    auth=TwitchAuthService('client',Store(),http,bus)
    listener=ListenerService(lambda _:None,Keys(),bus)
    app=create_app(store,listener,bus,sessions,static,twitch_auth=auth)
    with TestClient(app,base_url=sessions.origin) as client:
        yield client,sessions,auth,bus,listener
    asyncio.run(http.aclose())
    assert auth._closed


def login(c,s):
    r=c.post('/api/session',json={'token':s.issue_launch_token()},headers={'Origin':s.origin})
    return {'Origin':s.origin,'X-CSRF-Token':r.json()['csrf_token']}


def test_twitch_auth_flow_api_and_start_gate(twitch_api):
    c,s,auth,bus,listener=twitch_api
    assert c.get('/api/twitch/auth').status_code==401
    h=login(c,s)
    assert c.get('/api/twitch/auth').json()['status']=='disconnected'
    r=c.post('/api/listener/start',json={'expected_revision':2},headers=h)
    assert r.status_code==409 and r.json()['code']=='twitch_auth_required'
    assert listener.state().status=='stopped'
    r=c.post('/api/twitch/auth/start',headers=h)
    assert r.status_code==200 and r.json()['user_code']=='CODE'
    assert 'DEVICE_SECRET' not in r.text
    assert c.get('/api/twitch/auth').json()['status']=='pending'
    assert 'CODE' not in str(bus.recent())
    assert c.post('/api/twitch/auth/cancel',headers=h).json()['status']=='disconnected'
    assert c.delete('/api/twitch/auth',headers=h).status_code==200
    auth.client_id=''
    assert c.post('/api/twitch/auth/start',headers=h).json()['code']=='twitch_not_configured'


@pytest.mark.parametrize('method,path',[('POST','/api/twitch/auth/start'),('POST','/api/twitch/auth/cancel'),('DELETE','/api/twitch/auth')])
def test_auth_mutations_require_cookie_origin_and_csrf(twitch_api,method,path):
    c,s,*_=twitch_api
    assert c.request(method,path,headers={'Origin':s.origin}).status_code==401
    h=login(c,s)
    assert c.request(method,path,headers={'Origin':s.origin}).status_code==403
    assert c.request(method,path,headers={**h,'Origin':'http://evil'}).status_code==403

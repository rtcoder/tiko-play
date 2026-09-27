import asyncio
import pytest
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.session import SessionManager
from src.core.config_store import ConfigStore
from src.core.events import EventBus
from src.core.listener_service import ListenerService

class Keys:
    def disable(self): pass
    def enable(self,g): pass
    def submit(self,a): pass

@pytest.fixture
def api(tmp_path):
    static=tmp_path/'static';static.mkdir();(static/'index.html').write_text('<html>panel</html>')
    store=ConfigStore(tmp_path/'config.json');asyncio.run(store.load())
    bus=EventBus('test');sessions=SessionManager('test','http://127.0.0.1:8000')
    service=ListenerService(lambda _:None,Keys(),bus)
    app=create_app(store,service,bus,sessions,static)
    with TestClient(app,base_url=sessions.origin) as c:
        yield c,sessions,store,bus

def login(c,s):
    r=c.post('/api/session',json={'token':s.issue_launch_token()},headers={'Origin':s.origin})
    assert r.status_code==200
    return {'Origin':s.origin,'X-CSRF-Token':r.json()['csrf_token']}

def test_auth_save_conflict_and_refresh(api):
    c,s,store,bus=api
    assert c.get('/api/config').status_code==401
    assert c.get('/api/health').json()=={'ready':True}
    h=login(c,s);r=c.get('/api/config').json()
    assert c.get('/api/session').json()['csrf_token']==h['X-CSRF-Token']
    r['config']['streamer_id']='alice'
    body={'config':r['config'],'expected_revision':r['config_revision']}
    assert c.put('/api/config',json=body,headers={**h,'Origin':'http://evil'}).status_code==403
    assert c.put('/api/config',json=body,headers=h).status_code==200
    assert c.put('/api/config',json=body,headers=h).status_code==409
    assert c.post('/api/listener/stop',headers=h).status_code==202
    assert c.get('/api/unknown').status_code==404
    assert c.get('/',headers={'Host':'evil'}).status_code==403
    assert 'Content-Security-Policy' in c.get('/').headers

def test_websocket_snapshot_and_authorization(api):
    c,s,store,bus=api
    login(c,s);bus.publish('comment',{'user':'x','comment':'left'})
    with c.websocket_connect('ws://127.0.0.1:8000/api/events',headers={'Origin':s.origin}) as ws:
        snap=ws.receive_json()
        assert snap['type']=='snapshot' and snap['events'][0]['id']==1
        assert snap['state']['status']=='stopped'
    assert not bus.subscribers
    from starlette.websockets import WebSocketDisconnect
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect('ws://127.0.0.1:8000/api/events',headers={'Origin':'http://evil'}):pass

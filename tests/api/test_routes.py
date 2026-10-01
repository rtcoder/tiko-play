import asyncio

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.session import SessionManager
from src.core.config_store import ConfigStore
from src.core.events import EventBus
from src.core.listener_service import ListenerService


class Keys:
    def disable(self):
        pass

    def enable(self, g):
        pass

    def submit_reason(self, a, capacity=100):
        self.submit(a)

    def submit(self, a):
        pass


@pytest.fixture
def api(tmp_path, twitch_auth):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>panel</html>")
    store = ConfigStore(tmp_path / "config.json")
    asyncio.run(store.load())
    bus = EventBus("test")
    sessions = SessionManager("test", "http://127.0.0.1:8000")
    service = ListenerService(lambda _: None, Keys(), bus)
    app = create_app(store, service, bus, sessions, static, twitch_auth=twitch_auth)
    with TestClient(app, base_url=sessions.origin) as c:
        yield c, sessions, store, bus


def login(c, s):
    r = c.post(
        "/api/session",
        json={"token": s.issue_launch_token()},
        headers={"Origin": s.origin},
    )
    assert r.status_code == 200
    return {"Origin": s.origin, "X-CSRF-Token": r.json()["csrf_token"]}


def test_auth_save_conflict_and_refresh(api):
    c, s, store, bus = api
    assert c.get("/api/config").status_code == 401
    assert c.get("/api/health").json() == {"ready": True}
    h = login(c, s)
    r = c.get("/api/config").json()
    assert c.get("/api/session").json()["csrf_token"] == h["X-CSRF-Token"]
    r["config"]["tiktok"]["channel"] = "alice"
    body = {"config": r["config"], "expected_revision": r["config_revision"]}
    assert (
        c.put(
            "/api/config", json=body, headers={**h, "Origin": "http://evil"}
        ).status_code
        == 403
    )
    assert c.put("/api/config", json=body, headers=h).status_code == 200
    assert c.put("/api/config", json=body, headers=h).status_code == 409
    assert c.post("/api/listener/stop", headers=h).status_code == 202
    assert c.get("/api/unknown").status_code == 404
    assert c.get("/", headers={"Host": "evil"}).status_code == 403
    assert "Content-Security-Policy" in c.get("/").headers


def test_websocket_snapshot_and_authorization(api):
    c, s, store, bus = api
    login(c, s)
    bus.publish("comment", {"user": "x", "comment": "left"})
    with c.websocket_connect(
        "ws://127.0.0.1:8000/api/events", headers={"Origin": s.origin}
    ) as ws:
        snap = ws.receive_json()
        assert snap["type"] == "snapshot" and snap["events"][0]["id"] == 1
        assert snap["state"]["status"] == "stopped"
    assert not bus.subscribers
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect(
            "ws://127.0.0.1:8000/api/events", headers={"Origin": "http://evil"}
        ):
            pass


def test_second_launch_preserves_first_tab_csrf(api):
    c, s, store, bus = api
    first = login(c, s)
    second = login(c, s)
    assert second["X-CSRF-Token"] == first["X-CSRF-Token"]
    assert c.post("/api/listener/stop", headers=first).status_code == 202


def test_language_preferences_persist_without_touching_config(api):
    c, s, store, bus = api
    headers = login(c, s)
    before = store.path.read_bytes()
    response = c.put("/api/preferences", json={"language": "en"}, headers=headers)
    assert response.status_code == 200
    assert c.get("/api/state").json()["language"] == "en"
    assert c.get("/api/preferences").json() == {"language": "en"}
    assert store.path.read_bytes() == before
    assert bus.recent()[-1]["type"] == "preferences_changed"
    from src.core.preferences import PreferencesStore

    assert PreferencesStore(store.path.with_name("preferences.json")).language == "en"
    assert (
        c.put("/api/preferences", json={"language": "de"}, headers=headers).status_code
        == 422
    )
    assert (
        c.put(
            "/api/preferences", json={"language": "pl"}, headers={"Origin": s.origin}
        ).status_code
        == 403
    )
    assert c.get("/api/preferences").json() == {"language": "en"}


def test_saved_language_is_present_before_frontend_bootstraps(api):
    c, s, store, _bus = api
    (store.path.parent / "static" / "index.html").write_text(
        '<html lang="pl"><body>panel</body></html>'
    )
    h = login(c, s)
    for language in ("en", "pl"):
        c.put("/api/preferences", json={"language": language}, headers=h)
        assert f'<html lang="{language}">' in c.get("/").text


def test_language_change_is_broadcast_to_existing_tabs(api):
    c, s, _store, _bus = api
    h = login(c, s)
    with c.websocket_connect(
        "ws://127.0.0.1:8000/api/events", headers={"Origin": s.origin}
    ) as ws:
        assert ws.receive_json()["state"]["language"] == "en"
        assert (
            c.put("/api/preferences", json={"language": "pl"}, headers=h).status_code
            == 200
        )
        event = ws.receive_json()
        assert event["type"] == "preferences_changed"
        assert event["payload"] == {"language": "pl"}

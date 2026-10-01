import asyncio

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.session import SessionManager
from src.core.config_store import ConfigStore
from src.core.events import EventBus
from src.core.listener_service import ListenerService


@pytest.fixture
def youtube_api(tmp_path, twitch_auth):
    class Store:
        value = None
        lock = asyncio.Lock()

        async def load(self):
            return self.value

        async def save(self, value):
            self.value = value

        async def delete(self):
            self.value = None

    class Keys:
        def disable(self):
            pass

        def enable(self, _):
            pass

        def submit_reason(self, _, capacity=100):
            self.submit(_)

        def submit(self, _):
            raise AssertionError("unexpected keyboard")

    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("panel")
    store = ConfigStore(tmp_path / "config.json")
    asyncio.run(store.load())
    bus = EventBus("test")
    sessions = SessionManager("test", "http://127.0.0.1:8000")
    keys = Store()
    listener = ListenerService(lambda _: None, Keys(), bus)
    app = create_app(
        store,
        listener,
        bus,
        sessions,
        static,
        twitch_auth=twitch_auth,
        youtube_keys=keys,
    )
    with TestClient(app, base_url=sessions.origin) as client:
        yield client, sessions, listener, keys, bus


def login(c, sessions):
    response = c.post(
        "/api/session",
        json={"token": sessions.issue_launch_token()},
        headers={"Origin": sessions.origin},
    )
    return {"Origin": sessions.origin, "X-CSRF-Token": response.json()["csrf_token"]}


def test_key_is_write_only_and_mutations_are_protected(youtube_api):
    c, s, listener, keys, _bus = youtube_api
    assert c.get("/api/youtube/key").status_code == 401
    h = login(c, s)
    assert c.get("/api/youtube/key").json() == {"configured": False}
    assert (
        c.put(
            "/api/youtube/key",
            json={"key": "PRIVATE_KEY"},
            headers={"Origin": s.origin},
        ).status_code
        == 403
    )
    response = c.put("/api/youtube/key", json={"key": "PRIVATE_KEY"}, headers=h)
    assert response.status_code == 200 and response.json() == {"configured": True}
    assert keys.value == "PRIVATE_KEY"
    for path in ["/api/youtube/key", "/api/config", "/api/events/recent"]:
        assert "PRIVATE_KEY" not in c.get(path).text
    assert c.put("/api/youtube/key", json={"key": "  "}, headers=h).status_code == 422
    listener._change(active_platform="youtube", status="connected")
    assert c.delete("/api/youtube/key", headers=h).status_code == 409
    assert keys.value == "PRIVATE_KEY"
    listener._change(status="stopped")
    assert c.delete("/api/youtube/key", headers=h).json() == {"configured": False}


def test_youtube_start_requires_key_and_config_accepts_sources(youtube_api):
    c, s, listener, _keys, _bus = youtube_api
    h = login(c, s)
    cfg = c.get("/api/config").json()
    cfg["config"]["platform"] = "youtube"
    cfg["config"]["youtube"]["channel"] = "https://youtu.be/abcdefghijk"
    response = c.put(
        "/api/config",
        json={"config": cfg["config"], "expected_revision": cfg["config_revision"]},
        headers=h,
    )
    assert response.status_code == 200
    assert response.json()["config"]["youtube"]["channel"] == "abcdefghijk"
    response = c.post("/api/listener/start", json={"expected_revision": 2}, headers=h)
    assert (
        response.status_code == 409
        and response.json()["code"] == "youtube_key_required"
    )
    assert listener.state().status == "stopped"


async def test_stop_cancels_start_waiting_for_keyring(tmp_path, twitch_auth):
    from src.api.app import Revision
    from src.core.models import AppConfig, AppError

    entered, release = asyncio.Event(), asyncio.Event()

    class Vault:
        lock = asyncio.Lock()

        async def load(self):
            entered.set()
            await release.wait()
            return "secret"

    class Keys:
        def disable(self):
            pass

        def enable(self, _):
            raise AssertionError("must not enable keyboard")

        def submit_reason(self, _, capacity=100):
            self.submit(_)

        def submit(self, _):
            raise AssertionError("must not submit keyboard")

    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("panel")
    store = ConfigStore(tmp_path / "config.json")
    snap = await store.load()
    snap = await store.save(
        AppConfig(platform="youtube", youtube={"channel": "abcdefghijk"}), snap.revision
    )
    bus = EventBus("race")
    sessions = SessionManager("race", "http://127.0.0.1:8000")
    listener = ListenerService(lambda _: None, Keys(), bus)
    app = create_app(
        store,
        listener,
        bus,
        sessions,
        static,
        twitch_auth=twitch_auth,
        youtube_keys=Vault(),
    )
    start = next(
        route.endpoint
        for route in app.routes
        if getattr(route, "path", None) == "/api/listener/start"
    )
    task = asyncio.create_task(start(Revision(expected_revision=snap.revision)))
    try:
        await asyncio.wait_for(entered.wait(), 1)
        listener.request_stop()  # Same path used by tray and API Stop.
        release.set()
        try:
            await task
        except AppError as exc:
            assert exc.code == "start_cancelled"
        assert listener.state().status == "stopped"
    finally:
        release.set()
        await listener.stop()

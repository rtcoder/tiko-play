from typing import ClassVar

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from src.api.overlay import create_overlay_app
from src.core.overlay import OverlayStore


class Projection:
    def snapshot(self):
        return {
            "schema_version": 1,
            "sequence": 1,
            "mode": "direct",
            "paused": True,
            "commands": [],
            "last_action": None,
        }


@pytest.fixture
def overlay_api(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text('<html lang="pl">overlay</html>')
    (static / "assets").mkdir()
    store = OverlayStore(tmp_path / "overlay.json")
    app = create_overlay_app(
        store, Projection(), static, "http://127.0.0.1:18765", auth_timeout=0.03
    )
    with TestClient(app, base_url="http://127.0.0.1:18765") as c:
        yield c, store


def test_only_overlay_surface_and_security_headers(overlay_api):
    c, store = overlay_api
    assert c.get("/overlay").status_code == 200
    assert "script-src 'self'" in c.get("/overlay").headers["content-security-policy"]
    assert store.token not in c.get("/overlay").text
    assert (
        c.get(
            "/api/config", headers={"Authorization": "Bearer " + store.token}
        ).status_code
        == 404
    )
    assert c.post("/api/listener/start").status_code == 405
    assert c.get("/overlay", headers={"Host": "evil"}).status_code == 403


def test_ws_snapshot_rotation_and_read_only(overlay_api):
    c, store = overlay_api
    with c.websocket_connect(
        "ws://127.0.0.1:18765/overlay/events",
        headers={"Origin": "http://127.0.0.1:18765"},
    ) as ws:
        ws.send_json({"type": "auth", "token": store.token})
        assert ws.receive_json()["mode"] == "direct"
        store.rotate()
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()
    with c.websocket_connect(
        "ws://127.0.0.1:18765/overlay/events",
        headers={"Origin": "http://127.0.0.1:18765"},
    ) as ws:
        ws.send_json({"type": "auth", "token": store.token})
        assert ws.receive_json()["paused"]
        ws.send_json({"type": "start"})
        with pytest.raises(WebSocketDisconnect):
            ws.receive_json()


@pytest.mark.parametrize(
    "origin,token",
    [
        ("http://evil", "good"),
        ("http://127.0.0.1:18765", "bad"),
        ("http://127.0.0.1:18765", "żółć"),
        (None, "good"),
    ],
)
def test_ws_rejects_invalid_auth(overlay_api, origin, token):
    c, store = overlay_api
    with (
        pytest.raises(WebSocketDisconnect),
        c.websocket_connect(
            "ws://127.0.0.1:18765/overlay/events",
            headers={"Origin": origin} if origin else {},
        ) as ws,
    ):
        ws.send_json(
            {"type": "auth", "token": store.token if token == "good" else token}
        )
        ws.receive_json()


def test_ws_auth_deadline_and_malformed_payload(overlay_api):
    c, _ = overlay_api
    for payload in (None, "x" * 1025, "{"):
        with c.websocket_connect(
            "ws://127.0.0.1:18765/overlay/events",
            headers={"Origin": "http://127.0.0.1:18765"},
        ) as ws:
            if payload:
                ws.send_text(payload)
            with pytest.raises(WebSocketDisconnect):
                ws.receive_json()


async def test_slow_receiver_cannot_block_close_and_cleanup(tmp_path):
    import asyncio
    import json

    from src.api.overlay import create_overlay_app

    store = OverlayStore(tmp_path / "overlay.json")
    app = create_overlay_app(store, Projection(), tmp_path, "http://127.0.0.1:18765")
    endpoint = next(r.endpoint for r in app.routes if r.path == "/overlay/events")

    class SlowSocket:
        headers: ClassVar[dict[str, str]] = {"host": "127.0.0.1:18765", "origin": "http://127.0.0.1:18765"}
        authenticated = False
        close_attempted = False

        async def accept(self):
            pass

        async def receive_text(self):
            if not self.authenticated:
                self.authenticated = True
                return json.dumps({"type": "auth", "token": store.token})
            await asyncio.Future()

        async def send_json(self, _):
            await asyncio.Future()

        async def close(self, **_):
            self.close_attempted = True
            await asyncio.Future()

    ws = SlowSocket()
    await asyncio.wait_for(endpoint(ws), 2.6)
    assert ws.close_attempted


def test_operator_api_requires_panel_session_and_csrf(tmp_path, twitch_auth):
    import asyncio

    from src.api.app import create_app
    from src.api.session import SessionManager
    from src.core.config_store import ConfigStore
    from src.core.events import EventBus
    from src.core.listener_service import ListenerService
    from src.core.overlay import OverlayProjection
    from src.desktop.overlay_server import OverlayServer
    from tests.api.test_routes import Keys, login

    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("panel")
    config = ConfigStore(tmp_path / "config.json")
    asyncio.run(config.load())
    bus = EventBus("overlay-test")
    listener = ListenerService(lambda _: None, Keys(), bus)
    store = OverlayStore(tmp_path / "overlay.json")
    runtime = OverlayServer(
        store, OverlayProjection(listener, config, store, lambda: "pl"), static
    )
    sessions = SessionManager("overlay-test", "http://127.0.0.1:8000")
    app = create_app(
        config,
        listener,
        bus,
        sessions,
        static,
        twitch_auth=twitch_auth,
        overlay=runtime,
    )
    with TestClient(app, base_url=sessions.origin) as c:
        assert (
            c.get(
                "/api/overlay", headers={"Authorization": "Bearer " + store.token}
            ).status_code
            == 401
        )
        assert (
            c.post(
                "/api/session",
                json={"token": store.token},
                headers={"Origin": sessions.origin},
            ).status_code
            == 401
        )
        h = login(c, sessions)
        assert (
            c.post(
                "/api/overlay/rotate", headers={"Origin": sessions.origin}
            ).status_code
            == 403
        )
        initial = config.path.read_bytes()
        settings = {**store.settings.model_dump(), "font_size": 28}
        assert (
            c.put("/api/overlay", json=settings, headers=h).json()["settings"][
                "font_size"
            ]
            == 28
        )
        token = store.token
        assert c.post("/api/overlay/rotate", headers=h).status_code == 200
        assert store.token != token
        assert config.path.read_bytes() == initial

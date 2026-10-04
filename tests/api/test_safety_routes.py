import asyncio
from fastapi.testclient import TestClient
from src.api.app import create_app
from src.api.session import SessionManager
from src.core.output_guard import OutputGuard, TargetIdentity
from src.core.config_store import ConfigStore
from src.core.events import EventBus
from src.core.listener_service import ListenerService
from tests.api.test_routes import Keys, login


def test_safety_api_auth_validates_running_process_and_blocks_live_edits(
    tmp_path, twitch_auth
):
    (tmp_path / "index.html").write_text("<html>panel</html>")
    target = TargetIdentity(app="/game", pid=42, started="100", name="Game")

    class Focus:
        def targets(self):
            return [target]

        def current_target(self):
            return None

    guard = OutputGuard(Focus())
    store = ConfigStore(tmp_path / "config.json")
    asyncio.run(store.load())
    sessions = SessionManager("x", "http://127.0.0.1:8000")
    events = EventBus("x")
    service = ListenerService(lambda _: None, Keys(), events, guard=guard)
    app = create_app(
        store,
        service,
        events,
        sessions,
        tmp_path,
        twitch_auth=twitch_auth,
        output_guard=guard,
    )
    with TestClient(app, base_url=sessions.origin) as client:
        assert client.get("/api/output-safety").status_code == 401
        h = login(client, sessions)
        assert client.get("/api/output-safety").json()["targets"] == [
            target.model_dump()
        ]
        payload = {"enabled": True, "target": target.model_dump(), "key": "F10"}
        assert (
            client.put(
                "/api/output-safety", json=payload, headers={"Origin": sessions.origin}
            ).status_code
            == 403
        )
        assert (
            client.put("/api/output-safety", json=payload, headers=h).status_code == 200
        )
        payload["target"]["started"] = "101"
        assert (
            client.put("/api/output-safety", json=payload, headers=h).status_code == 422
        )
        assert guard.state()["target"]["started"] == "100"
        service._change(status="connecting")
        assert (
            client.put(
                "/api/output-safety", json={"enabled": False}, headers=h
            ).status_code
            == 409
        )
        assert client.post("/api/output-safety/resume", headers=h).status_code == 409

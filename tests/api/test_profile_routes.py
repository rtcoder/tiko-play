import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.session import SessionManager
from src.core.config_store import ConfigStore
from src.core.events import EventBus
from src.core.listener_service import ListenerService
from tests.api.test_routes import Keys, login


@pytest.fixture
def profiles_api(tmp_path, twitch_auth):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>panel</html>")
    store = ConfigStore(tmp_path / "config.json")
    asyncio.run(store.load())
    events = EventBus("test")
    sessions = SessionManager("test", "http://127.0.0.1:8000")
    service = ListenerService(lambda _: None, Keys(), events)
    app = create_app(store, service, events, sessions, static, twitch_auth=twitch_auth)
    with TestClient(app, base_url=sessions.origin) as client:
        yield client, sessions, store, service


def test_portable_import_preview_auth_limits_and_no_write(profiles_api):
    c, sessions, store, _ = profiles_api
    payload = {
        "format_version": 1,
        "name": "Retro",
        "mappings": [{"trigger": "2", "keys": ["down"]}],
    }
    assert (
        c.post(
            "/api/profiles/import-preview",
            json=payload,
            headers={"Origin": sessions.origin},
        ).status_code
        == 401
    )
    h = login(c, sessions)
    original = store.path.read_bytes()
    result = c.post("/api/profiles/import-preview", json=payload, headers=h)
    assert result.status_code == 200
    assert result.json()["name"] == "Retro"
    assert result.json()["filters"]["tiktok"] == ""
    assert store.path.read_bytes() == original
    assert (
        c.post(
            "/api/profiles/import-preview", content=b" " * (1024 * 1024 + 1), headers=h
        ).status_code
        == 413
    )
    assert (
        c.post(
            "/api/profiles/import-preview",
            json={**payload, "format_version": 2},
            headers=h,
        ).status_code
        == 422
    )


@pytest.mark.parametrize("status", ["connecting", "connected", "stopping"])
def test_switch_rejected_while_listener_is_busy(profiles_api, status):
    c, sessions, store, service = profiles_api
    h = login(c, sessions)
    body = c.get("/api/config").json()
    body["config"]["profiles"].append({"id": "other", "name": "Other", "mappings": []})
    body["config"]["active_profile_id"] = "other"
    service._change(status=status)
    response = c.put(
        "/api/config",
        json={"config": body["config"], "expected_revision": 1},
        headers=h,
    )
    assert response.status_code == 409
    assert response.json()["code"] == "profiles_busy"
    assert len(store.snapshot().config.profiles) == 1


def test_create_switch_persist_export_and_conflict(profiles_api):
    c, sessions, store, service = profiles_api
    h = login(c, sessions)
    body = c.get("/api/config").json()
    body["config"]["profiles"].append(
        {
            "id": "other",
            "name": "Other",
            "filters": {"tiktok": "private"},
            "mappings": [{"id": "m", "trigger": "go", "keys": ["left"]}],
        }
    )
    body["config"]["active_profile_id"] = "other"
    write = {"config": body["config"], "expected_revision": 1}
    assert c.put("/api/config", json=write, headers=h).status_code == 200
    assert c.put("/api/config", json=write, headers=h).status_code == 409
    assert json.loads(store.path.read_text())["active_profile_id"] == "other"
    exported = c.get("/api/profiles/other/export")
    assert exported.status_code == 200
    assert "private" not in exported.text
    assert exported.json()["mappings"] == [{"trigger": "go", "keys": ["left"]}]
    assert c.get("/api/profiles/missing/export").status_code == 404
    invalid = c.get("/api/config").json()
    invalid["config"]["profiles"] = []
    assert (
        c.put(
            "/api/config",
            json={"config": invalid["config"], "expected_revision": 2},
            headers=h,
        ).status_code
        == 422
    )
    templates = c.get("/api/profile-templates").json()
    assert {"numpad", "hugo", "tetris", "pacman", "sokoban", "baba"} <= {
        t["id"] for t in templates
    }

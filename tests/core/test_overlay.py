import json
import os
import stat

from src.core.events import EventBus
from src.core.listener_service import ListenerService
from src.core.models import AppConfig
from src.core.overlay import OverlayProjection, OverlaySettings, OverlayStore
from tests.core.test_listener_service import Client, Keyboard, settle


def test_token_persists_rotates_and_is_private(tmp_path):
    path = tmp_path / "overlay.json"
    store = OverlayStore(path)
    token = store.token
    assert len(token) >= 43
    assert OverlayStore(path).token == token
    if os.name != "nt":  # Windows chmod exposes only the read-only flag.
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    store.rotate()
    assert store.token != token
    assert OverlayStore(path).token == store.token
    assert "token" not in store.settings.model_dump()


async def test_public_projection_tracks_executed_action_not_recent_chat(tmp_path):
    from src.core.config_store import ConfigStore

    config = ConfigStore(tmp_path / "config.json")
    await config.load()
    snap = await config.save(
        AppConfig(
            tiktok={"channel": "private", "target_user": "alice"},
            countdown_enabled=False,
            mappings=[{"id": "go", "trigger": "go", "keys": ["up"]}],
        ),
        1,
    )
    keys, client = Keyboard(), Client()
    service = ListenerService(lambda _: client, keys, EventBus("test"))
    store = OverlayStore(tmp_path / "overlay.json")
    projection = OverlayProjection(service, config, store, lambda: "pl")
    assert projection.snapshot()["paused"]
    service.start(snap)
    await settle()
    try:
        await client.callback("alice", "GO")
        action = keys.actions[0]
        assert action.comment == "GO" and action.actor_id == "alice"
        assert projection.snapshot()["last_action"] is None
        service.keyboard_result(
            "executed",
            {
                "generation": 1,
                "mapping_id": "go",
                "actor_id": "alice",
                "comment": "GO",
                "action": action.definition.model_dump(mode="json"),
            },
        )
        await client.callback("bob", "private message")
        public = projection.snapshot()
        assert public["last_action"]["comment"] == "GO"
        assert "actor" not in public["last_action"]
        assert not public["paused"]
        assert "private" not in json.dumps(public)
        assert "alice" not in json.dumps(public)
        assert projection.snapshot()["sequence"] == public["sequence"]
        store.save(store.settings.model_copy(update={"show_actor": True}))
        assert projection.snapshot()["last_action"]["actor"] == "alice"
        service.keyboard_result("executed", {"generation": 0, "actor_id": "stale"})
        assert projection.snapshot()["last_action"]["actor"] == "alice"
        await service.stop()
        service.start(snap)
        assert projection.snapshot()["last_action"] is None
    finally:
        await service.stop()


def test_presentation_validation():
    import pytest
    from pydantic import ValidationError

    for patch in [
        {"port": 80},
        {"font_size": 49},
        {"accent": "url(https://evil)"},
        {"extra": True},
    ]:
        with pytest.raises(ValidationError):
            OverlaySettings(**patch)


async def test_executor_reports_the_actual_author_comment_and_completion():
    import asyncio
    import threading

    from src.core.keyboard import KeyAction, KeyboardExecutor

    done = threading.Event()
    reports = []
    released = []

    class Port:
        def key_down(self, key):
            pass

        def key_up(self, key):
            released.append(key)

    def report(kind, payload):
        reports.append((kind, payload, list(released)))
        done.set()

    executor = KeyboardExecutor(Port(), clock=lambda: 0, report=report)
    try:
        executor.enable(1)
        executor.submit(
            KeyAction(("up",), 1, 0, mapping_id="move", actor_id="alice", comment="8")
        )
        assert await asyncio.to_thread(done.wait, 1)
        kind, payload, releases = reports[0]
        assert kind == "executed" and releases == ["up"]
        assert payload["actor_id"] == "alice" and payload["comment"] == "8"
    finally:
        await executor.close()

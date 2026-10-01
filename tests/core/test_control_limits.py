import pytest
from src.core.models import AppConfig, ConfigSnapshot
from src.core.simulation import simulate, SimulationMessage


def config(**limits):
    return AppConfig(
        profiles=[
            {
                "id": "p",
                "name": "Gra",
                "limits": limits,
                "mappings": [
                    {"id": "x", "trigger": "x", "keys": ["a"]},
                    {"id": "y", "trigger": "y", "keys": ["b"]},
                ],
            }
        ],
        active_profile_id="p",
    )


def test_viewer_limit_applies_across_commands_not_other_viewers():
    cfg = config(viewer_cooldown_ms=1000, action_cooldown_ms=0)
    messages = [
        SimulationMessage(offset_ms=t, user_id=u, comment=c)
        for t, u, c in [
            (0, "a", "x"),
            (100, "a", "y"),
            (100, "b", "y"),
            (1000, "a", "y"),
        ]
    ]
    result = simulate(ConfigSnapshot(cfg, 1), tuple(messages))
    assert [d.reason for d in result.decisions] == [
        "planned",
        "user_cooldown",
        "planned",
        "planned",
    ]


def test_limits_reject_invalid_values():
    from pydantic import ValidationError

    for limits in [
        {"queue_capacity": 0},
        {"queue_capacity": 101},
        {"action_ttl_ms": 99},
        {"viewer_cooldown_ms": -1},
        {"action_cooldown_ms": True},
    ]:
        with pytest.raises(ValidationError):
            config(**limits)


def test_check_is_readonly_commit_boundary_and_bounded_viewers():
    from src.core.rate_limits import RateLimiter, ControlLimits

    limiter = RateLimiter(ControlLimits(viewer_cooldown_ms=1000))
    assert limiter.check("a", "x", 0).reason is None
    assert limiter.check("a", "x", 0).reason is None
    limiter.commit("a", "x", 0)
    assert limiter.check("b", "x", 0.299).reason == "action_cooldown"
    assert limiter.check("b", "x", 0.300).reason is None
    assert limiter.check("a", "y", 0.999).reason == "user_cooldown"
    assert limiter.check("a", "y", 1).reason is None
    for i in range(10001):
        limiter.commit(str(i), "x", 2)
    assert len(limiter.viewers) == 10000
    assert "0" not in limiter.viewers
    limiter.prune(122)
    assert not limiter.viewers


def test_full_queue_does_not_consume_viewer_or_action_cooldown():
    cfg = config(
        viewer_cooldown_ms=500,
        action_cooldown_ms=300,
        queue_capacity=1,
        action_ttl_ms=5000,
    )
    data = cfg.model_dump()
    data["profiles"][0]["mappings"][0]["action"] = {
        "steps": [{"type": "wait", "duration_ms": 1000}]
    }
    cfg = AppConfig.model_validate(data)
    messages = [
        SimulationMessage(offset_ms=t, user_id=u, comment=c)
        for t, u, c in [
            (0, "a", "x"),
            (300, "b", "x"),
            (900, "c", "y"),
            (1000, "c", "y"),
        ]
    ]
    result = simulate(ConfigSnapshot(cfg, 1), tuple(messages))
    assert [d.reason for d in result.decisions] == [
        "planned",
        "planned",
        "queue_full",
        "planned",
    ]


async def test_v6_migration_backup_and_portable_limits(tmp_path):
    import json
    from src.core.config_store import ConfigStore
    from src.core.profiles import export_profile, import_profile

    raw = config(viewer_cooldown_ms=1234).model_dump()
    raw["version"] = 6
    del raw["profiles"][0]["limits"]
    path = tmp_path / "config.json"
    original = json.dumps(raw)
    path.write_text(original)
    cfg = (await ConfigStore(path).load()).config
    assert cfg.version == 7 and cfg.active_profile.limits.action_cooldown_ms == 300
    assert (tmp_path / "config.v6.backup.json").read_text() == original
    profile = config(viewer_cooldown_ms=1234).active_profile
    assert import_profile(export_profile(profile)).limits == profile.limits
    assert (
        import_profile(
            {"format_version": 2, "name": "old", "mappings": []}
        ).limits.viewer_cooldown_ms
        == 0
    )


async def test_live_spam_is_bounded_and_resets_without_old_callbacks():
    import asyncio
    from test_listener_service import Client, Keyboard, settle
    from src.core.events import EventBus
    from src.core.listener_service import ListenerService

    cfg = config(viewer_cooldown_ms=1000, action_cooldown_ms=0)
    cfg = cfg.model_copy(
        update={
            "tiktok": AppConfig(tiktok={"channel": "test"}).tiktok,
            "countdown_enabled": False,
        }
    )
    client = Client()
    keyboard = Keyboard()
    events = EventBus("limits")
    service = ListenerService(lambda _: client, keyboard, events, clock=lambda: 0)
    snap = ConfigSnapshot(cfg, 1)
    service.start(snap)
    await settle()
    try:
        callback = client.callback
        for _ in range(10000):
            await callback("a", "x")
        stats = service.state().control_stats
        assert stats["counts"] == {"accepted": 1, "user_cooldown": 9999}
        assert len(stats["recent"]) == 30 and len(keyboard.actions) == 1
        assert len(events.recent()) < 10
        await asyncio.sleep(1.05)
        assert len([e for e in events.recent() if e["type"] == "control_stats"]) == 1
        old = service.state().generation
        await service.stop()
        service.start(snap)
        await settle()
        await callback("a", "x")
        service.keyboard_result("skipped", {"generation": old, "reason": "expired"})
        assert service.state().control_stats["counts"] == {}
        await client.callback("a", "x")
        assert service.state().control_stats["counts"] == {"accepted": 1}
    finally:
        await service.stop()


async def test_live_admission_rejection_does_not_consume_cooldown():
    from test_listener_service import Client, Keyboard, settle
    from src.core.events import EventBus
    from src.core.listener_service import ListenerService

    class RejectOnce(Keyboard):
        rejected = False

        def submit_reason(self, action, capacity=100):
            assert capacity == 1
            if not self.rejected:
                self.rejected = True
                return "queue_full"
            self.actions.append(action)

    cfg = config(viewer_cooldown_ms=1000, queue_capacity=1, action_ttl_ms=4500)
    cfg = cfg.model_copy(
        update={
            "tiktok": AppConfig(tiktok={"channel": "test"}).tiktok,
            "countdown_enabled": False,
        }
    )
    keyboard = RejectOnce()
    client = Client()
    service = ListenerService(
        lambda _: client, keyboard, EventBus("x"), clock=lambda: 1
    )
    service.start(ConfigSnapshot(cfg, 1))
    await settle()
    try:
        await client.callback("a", "x")
        await client.callback("a", "x")
        assert len(keyboard.actions) == 1
        assert keyboard.actions[0].expires_at == 5.5
        assert service.state().control_stats["counts"] == {
            "queue_full": 1,
            "accepted": 1,
        }
        service.request_stop()
        service.keyboard_result(
            "executed", {"generation": 1, "actor_id": "a", "comment": "x"}
        )
        assert service.last_executed is None
        assert service.state().control_stats["counts"]["stale_epoch"] == 1
    finally:
        await service.stop()


@pytest.mark.parametrize("age, expected", [(1.0, "executed"), (1.001, "skipped")])
async def test_executor_capacity_expiry_and_stop_reports(age, expected):
    import asyncio, threading
    from src.core.keyboard import KeyboardExecutor, KeyAction

    entered = threading.Event()
    release = threading.Event()
    finished = threading.Event()
    now = [0.0]
    reports = []

    class Port:
        def key_down(self, key):
            if key == "a":
                entered.set()
                release.wait(2)

        def key_up(self, key):
            pass

    def report(kind, payload):
        reports.append((kind, payload))
        if payload.get("mapping_id") == "b":
            finished.set()

    executor = KeyboardExecutor(Port(), clock=lambda: now[0], report=report)
    try:
        executor.enable(1)
        executor.submit(KeyAction(("a",), 1, 0))
        assert await asyncio.to_thread(entered.wait, 1)
        assert (
            executor.submit_reason(KeyAction(("b",), 1, 0, mapping_id="b"), capacity=1)
            is None
        )
        assert (
            executor.submit_reason(KeyAction(("c",), 1, 0), capacity=1) == "queue_full"
        )
        now[0] = age
        release.set()
        assert await asyncio.to_thread(finished.wait, 1)
        row = next(row for row in reports if row[1].get("mapping_id") == "b")
        assert row[0] == expected
        if expected == "skipped":
            assert row[1]["reason"] == "expired"
    finally:
        release.set()
        await executor.close()

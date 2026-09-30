import pytest
from pydantic import ValidationError

from src.core.matching import Matcher
from src.core.models import AppConfig, ConfigSnapshot
from src.core.simulation import SimulationMessage, SimulationRequest, simulate


def snapshot(**kwargs):
    return ConfigSnapshot(
        AppConfig(mappings=[{"id": "go", "trigger": "go", "keys": ["up"]}], **kwargs), 7
    )


def msg(at, text="go", user="alice"):
    return SimulationMessage(offset_ms=at, user_id=user, comment=text)


def test_matcher_resolve_is_pure_and_reports_reasons():
    matcher = Matcher(snapshot(tiktok={"target_user": "alice"}).config, lambda: 0)
    assert matcher.resolve("bob", "go").reason == "user_filtered"
    assert matcher.resolve("alice", "unknown").reason == "no_mapping"
    assert matcher.resolve("alice", " GO ").mapping_id == "go"
    assert matcher.resolve("alice", "go").reason == "matched"
    assert matcher.match_mapping("alice", "go").id == "go"
    assert matcher.decide("alice", "go").reason == "action_cooldown"


def test_simulation_matches_live_decisions_and_is_repeatable():
    snap = snapshot(tiktok={"target_user": "alice"})
    messages = (
        msg(0),
        msg(0),
        msg(100, user="bob"),
        msg(200, text="missing"),
        msg(300),
    )
    now = [0]
    matcher = Matcher(snap.config, lambda: now[0])
    expected = []
    for message in messages:
        now[0] = message.offset_ms / 1000
        reason = matcher.decide(message.user_id, message.comment).reason
        expected.append("planned" if reason == "matched" else reason)
    result = simulate(snap, messages)
    assert [d.reason for d in result.decisions] == expected
    assert result.config_revision == 7
    assert result == simulate(snap, messages)
    assert result.decisions[0].steps[0].keys == ("up",)


def test_stable_sort_preserves_order_of_ties():
    result = simulate(snapshot(), (msg(500), msg(0), msg(0)))
    assert [d.message_index for d in result.decisions] == [1, 2, 0]
    assert [d.reason for d in result.decisions] == [
        "planned",
        "action_cooldown",
        "planned",
    ]


def test_hold_expires_queued_message_and_records_steps():
    snap = ConfigSnapshot(
        AppConfig(
            mappings=[
                {
                    "id": "hold",
                    "trigger": "hold",
                    "action": {
                        "steps": [
                            {
                                "type": "hold",
                                "keys": ["ctrl", "a"],
                                "duration_ms": 2000,
                            },
                            {"type": "wait", "duration_ms": 100},
                        ]
                    },
                },
                {"id": "go", "trigger": "go", "keys": ["up"]},
            ]
        ),
        1,
    )
    result = simulate(snap, (msg(0, "hold"), msg(300)))
    first, second = result.decisions
    assert first.reason == "planned" and first.finished_at_ms == 2100
    assert [(s.start_ms, s.end_ms) for s in first.steps] == [(0, 2000), (2000, 2100)]
    assert second.reason == "expired" and not second.steps
    assert second.decided_at_ms == 2100


def test_queue_capacity_excludes_running_action():
    mappings = [
        {
            "id": str(i),
            "trigger": str(i),
            "action": {"steps": [{"type": "hold", "keys": ["a"], "duration_ms": 3000}]},
        }
        for i in range(102)
    ]
    result = simulate(
        ConfigSnapshot(AppConfig(mappings=mappings), 1),
        tuple(msg(0, str(i)) for i in range(102)),
    )
    assert result.decisions[0].reason == "planned"
    assert sum(d.reason == "expired" for d in result.decisions) == 100
    assert result.decisions[-1].reason == "queue_full"


@pytest.mark.parametrize(
    "platform,actor,expected",
    [
        ("tiktok", "ALICE", "user_filtered"),
        ("twitch", "ALICE", "planned"),
        ("kick", "ALICE", "planned"),
        ("youtube", "alice", "planned"),
    ],
)
def test_platform_filters(platform, actor, expected):
    snap = snapshot(**{platform: {"target_user": "alice"}})
    report = simulate(snap, (msg(0, user=actor),), platform=platform)
    assert report.decisions[0].reason == expected
    assert snap.config.platform == "tiktok"


@pytest.mark.parametrize(
    "data",
    [
        {"offset_ms": -1},
        {"offset_ms": 60001},
        {"offset_ms": 1.5},
        {"offset_ms": True},
        {"comment": "x" * 2001},
        {"user_id": ""},
    ],
)
def test_message_limits(data):
    with pytest.raises(ValidationError):
        SimulationMessage.model_validate(
            {"offset_ms": 0, "user_id": "alice", "comment": "go", **data}
        )


def test_scenario_limits():
    with pytest.raises(ValidationError):
        SimulationRequest(expected_revision=1, messages=[])
    with pytest.raises(ValidationError):
        SimulationRequest(expected_revision=1, messages=[msg(0)] * 1001)


def test_never_constructs_real_output_or_chat(monkeypatch):
    from src.adapters.chat import ChatAdapterFactory
    from src.adapters.pyautogui_keyboard import PyAutoGUIKeyboard

    def forbidden(*args, **kwargs):
        raise AssertionError("Real integration accessed")

    monkeypatch.setattr(PyAutoGUIKeyboard, "__init__", forbidden)
    monkeypatch.setattr(ChatAdapterFactory, "__init__", forbidden)
    assert simulate(snapshot(), (msg(0),)).decisions[0].reason == "planned"


@pytest.mark.parametrize("duration, reason", [(1300, "planned"), (1301, "expired")])
def test_queue_ttl_boundary(duration, reason):
    snap = ConfigSnapshot(
        AppConfig(
            mappings=[
                {
                    "id": "hold",
                    "trigger": "hold",
                    "action": {
                        "steps": [
                            {"type": "hold", "keys": ["a"], "duration_ms": duration}
                        ]
                    },
                },
                {"id": "go", "trigger": "go", "keys": ["up"]},
            ]
        ),
        1,
    )
    result = simulate(snap, (msg(0, "hold"), msg(300)))
    assert result.decisions[1].reason == reason
    assert result.decisions[1].decided_at_ms == duration


def test_selects_saved_profile_without_changing_active_profile():
    snap = ConfigSnapshot(
        AppConfig(
            active_profile_id="a",
            profiles=[
                {
                    "id": "a",
                    "name": "First",
                    "mappings": [{"id": "go", "trigger": "go", "keys": ["up"]}],
                },
                {
                    "id": "b",
                    "name": "Second",
                    "mappings": [{"id": "go", "trigger": "go", "keys": ["down"]}],
                },
            ],
        ),
        3,
    )
    before = snap.config.model_dump()
    result = simulate(snap, (msg(0),), profile_id="b")
    assert result.profile_name == "Second"
    assert result.decisions[0].steps[0].keys == ("down",)
    assert snap.config.model_dump() == before


async def test_simulation_does_not_touch_running_live_output_history_or_cooldown():
    from src.core.events import EventBus
    from src.core.listener_service import ListenerService
    from tests.core.test_listener_service import Client, Keyboard, settle

    client, keys, bus = Client(), Keyboard(), EventBus("simulation-isolation")
    snap = snapshot(tiktok={"channel": "test"}, countdown_enabled=False)
    service = ListenerService(lambda _: client, keys, bus, clock=lambda: 0)
    service.start(snap)
    await settle()
    try:
        assert service.state().status == "connected"
        before = service.state(), bus.recent(), list(keys.actions)
        assert simulate(snap, (msg(0), msg(100))).planned_count == 1
        assert (service.state(), bus.recent(), keys.actions) == before
        await client.callback("alice", "go")
        assert len(keys.actions) == 1  # simulation did not consume the LIVE cooldown
        simulate(snap, (msg(0),))
        await client.callback("alice", "go")
        assert len(keys.actions) == 1  # simulation did not reset the LIVE cooldown
    finally:
        await service.stop()


def test_virtual_time_is_exact_at_decimal_boundaries():
    result = simulate(snapshot(), tuple(msg(t) for t in (0, 300, 600, 900, 1200)))
    assert all(d.reason == "planned" for d in result.decisions)
    snap = ConfigSnapshot(
        AppConfig(
            mappings=[
                {
                    "id": "hold",
                    "trigger": "hold",
                    "action": {
                        "steps": [{"type": "hold", "keys": ["a"], "duration_ms": 1118}]
                    },
                },
                {"id": "go", "trigger": "go", "keys": ["up"]},
            ]
        ),
        1,
    )
    assert simulate(snap, (msg(0, "hold"), msg(118))).decisions[1].reason == "planned"

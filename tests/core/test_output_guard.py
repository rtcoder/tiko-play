import pytest
from src.core.keyboard import KeyboardExecutor, KeyAction


async def test_guard_denies_key_and_fences_queue():
    calls = []
    reports = []

    class Port:
        def key_down(self, key):
            calls.append(key)

        def key_up(self, key):
            pass

    keyboard = KeyboardExecutor(
        Port(), output_check=lambda: False, report=lambda *r: reports.append(r)
    )
    keyboard.enable(1)
    keyboard.submit(KeyAction(("a",), 1, keyboard.clock()))
    import asyncio

    for _ in range(50):
        if reports:
            break
        await asyncio.sleep(0.01)
    await keyboard.close()
    assert not calls
    assert any(kind == "focus_lost" for kind, _ in reports)


from src.core.output_guard import TargetIdentity, OutputGuard


def target(**patch):
    return TargetIdentity(
        **({"app": "/game", "pid": 42, "started": "100", "name": "Game"} | patch)
    )


class Focus:
    current = target()

    def current_target(self):
        return self.current

    def targets(self):
        return [target()]


def test_guard_fails_closed_on_pid_reuse_and_api_error():
    focus = Focus()
    guard = OutputGuard(focus)
    assert guard.can_execute()
    guard.configure(True, None)
    assert not guard.can_execute()
    guard.configure(True, target())
    assert guard.can_execute()
    for current in [None, target(pid=43), target(started="101"), target(app="/other")]:
        focus.current = current
        assert not guard.can_execute()

    def broken():
        raise OSError("permissions")

    focus.current_target = broken
    assert not guard.can_execute()


async def test_loss_during_hold_releases_key_and_never_starts_next_step():
    import asyncio, threading
    from src.core.actions import ActionDefinition

    calls = []
    entered = threading.Event()
    released = threading.Event()
    allowed = [True]

    class Port:
        def key_down(self, key):
            calls.append(("down", key))
            entered.set()

        def key_up(self, key):
            calls.append(("up", key))
            released.set()

    keyboard = KeyboardExecutor(Port(), output_check=lambda: allowed[0])
    keyboard.enable(1)
    definition = ActionDefinition.model_validate(
        {
            "steps": [
                {"type": "hold", "keys": ["a"], "duration_ms": 3000},
                {"type": "press", "keys": ["b"]},
            ]
        }
    )
    keyboard.submit(KeyAction((), 1, keyboard.clock(), definition=definition))
    assert await asyncio.to_thread(entered.wait, 1)
    allowed[0] = False
    assert await asyncio.to_thread(released.wait, 1)
    assert calls == [("down", "a"), ("up", "a")]
    allowed[0] = True
    assert not keyboard.submit(KeyAction(("b",), 1, keyboard.clock()))
    await keyboard.close()


async def test_focus_requires_stable_countdown_and_explicit_resume():
    import asyncio
    from test_listener_service import Client, Keyboard, settle
    from src.core.listener_service import ListenerService
    from src.core.events import EventBus
    from src.core.models import AppConfig, ConfigSnapshot

    focus = Focus()
    focus.current = None
    guard = OutputGuard(focus)
    guard.configure(True, target())
    keys = Keyboard()
    client = Client()
    now = [0.0]
    service = ListenerService(
        lambda _: client, keys, EventBus("x"), clock=lambda: now[0], guard=guard
    )
    snap = ConfigSnapshot(
        AppConfig(tiktok={"channel": "test"}, countdown_enabled=False), 1
    )
    service.start(snap)
    await settle()
    try:
        assert service.state().output == "waiting_focus" and not keys.enabled
        focus.current = target()
        await asyncio.sleep(0.06)
        assert service.state().output == "countdown"
        now[0] = 3.01
        await asyncio.sleep(0.06)
        assert service.state().output == "enabled" and keys.enabled
        focus.current = None
        await asyncio.sleep(0.06)
        assert service.state().output == "paused_focus" and not keys.enabled
        focus.current = target()
        now[0] = 50
        await asyncio.sleep(0.06)
        assert service.state().output == "paused_focus" and not keys.enabled
        service.resume_output()
        await asyncio.sleep(0.06)
        now[0] = 52.99
        await asyncio.sleep(0.06)
        assert not keys.enabled
        service.request_stop()
        now[0] = 100
        await asyncio.sleep(0.06)
        assert not keys.enabled
    finally:
        await service.stop()

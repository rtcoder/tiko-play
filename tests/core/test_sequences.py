import asyncio
import threading

import pytest

from src.core.actions import ActionDefinition
from src.core.keyboard import KeyAction, KeyboardExecutor
from src.core.models import AppError


class Port:
    def __init__(self):
        self.calls = []
        self.down = threading.Event()

    def key_down(self, key):
        self.calls.append(("down", key))
        self.down.set()

    def key_up(self, key):
        self.calls.append(("up", key))


def action(k, steps, generation=1):
    return KeyAction(
        (),
        generation,
        k.clock(),
        definition=ActionDefinition(steps=steps),
        mapping_id="m",
        actor_id="viewer",
    )


async def until(predicate):
    for _ in range(200):
        if predicate():
            return
        await asyncio.sleep(0.005)
    assert predicate()


async def test_sequence_order_and_reverse_chord_release():
    p = Port()
    reports = []
    k = KeyboardExecutor(p, report=lambda *a: reports.append(a))
    k.enable(1)
    try:
        k.submit(
            action(
                k,
                [
                    {"type": "press", "keys": ["ctrl", "a"]},
                    {"type": "wait", "duration_ms": 10},
                    {"type": "hold", "keys": ["left"], "duration_ms": 50},
                ],
            )
        )
        await until(lambda: reports)
        assert p.calls == [
            ("down", "ctrl"),
            ("down", "a"),
            ("up", "a"),
            ("up", "ctrl"),
            ("down", "left"),
            ("up", "left"),
        ]
        assert reports[0][0] == "executed"
    finally:
        await k.close()


@pytest.mark.parametrize("first", ["hold", "wait"])
async def test_disable_interrupts_waits_and_drops_following_steps(first):
    p = Port()
    k = KeyboardExecutor(p)
    k.enable(1)
    steps = [
        {
            "type": first,
            "duration_ms": 3000,
            **({"keys": ["a"]} if first == "hold" else {}),
        },
        {"type": "press", "keys": ["b"]},
    ]
    try:
        k.submit(action(k, steps))
        if first == "hold":
            assert await asyncio.to_thread(p.down.wait, 1)
        else:
            await asyncio.sleep(0.02)
        k.disable()
        await k.close(0.5)
        assert not k._thread.is_alive()
        assert p.calls == ([("down", "a"), ("up", "a")] if first == "hold" else [])
    finally:
        await k.close()


async def test_failed_second_down_releases_both_attempted_keys():
    class Broken(Port):
        def key_down(self, key):
            super().key_down(key)
            if key == "a":
                raise RuntimeError("partial OS failure")

    p = Broken()
    reports = []
    k = KeyboardExecutor(p, report=lambda *a: reports.append(a))
    k.enable(1)
    try:
        k.submit(action(k, [{"type": "press", "keys": ["ctrl", "a"]}]))
        await until(lambda: reports)
        assert p.calls[-2:] == [("up", "a"), ("up", "ctrl")]
        assert not k.submit(action(k, [{"type": "press", "keys": ["b"]}]))
    finally:
        await k.close()


async def test_failed_release_latches_output_fault_and_releases_other_keys():
    class Broken(Port):
        def key_up(self, key):
            super().key_up(key)
            if key == "a":
                raise RuntimeError("release denied")

    p = Broken()
    reports = []
    k = KeyboardExecutor(p, report=lambda *a: reports.append(a))
    k.enable(1)
    try:
        k.submit(action(k, [{"type": "press", "keys": ["ctrl", "a"]}]))
        await until(lambda: reports)
        assert p.calls[-2:] == [("up", "a"), ("up", "ctrl")]
        assert reports[0][1]["code"] == "keyboard_release_error"
        with pytest.raises(AppError):
            k.enable(2)
    finally:
        await k.close()


async def test_epoch_invalidates_inflight_even_if_generation_reused():
    p = Port()
    k = KeyboardExecutor(p)
    k.enable(1)
    try:
        k.submit(
            action(
                k,
                [
                    {"type": "hold", "keys": ["a"], "duration_ms": 3000},
                    {"type": "press", "keys": ["b"]},
                ],
            )
        )
        assert await asyncio.to_thread(p.down.wait, 1)
        old = k.output_epoch
        k.disable()
        k.enable(1)
        stale = KeyAction(("c",), 1, k.clock(), output_epoch=old)
        assert not k.submit(stale)
        k.submit(action(k, [{"type": "press", "keys": ["d"]}]))
        await until(lambda: ("up", "d") in p.calls)
        assert p.calls == [("down", "a"), ("up", "a"), ("down", "d"), ("up", "d")]
    finally:
        await k.close()


@pytest.mark.parametrize("stop", [True, False])
async def test_listener_stop_or_disconnect_releases_hold(stop):
    from src.core.events import EventBus
    from src.core.listener_service import ListenerService
    from src.core.models import AppConfig, ConfigSnapshot
    from tests.core.test_listener_service import Client

    p = Port()
    k = KeyboardExecutor(p)
    client = Client()
    listener = ListenerService(lambda _: client, k, EventBus("sequence-test"))
    config = AppConfig(
        tiktok={"channel": "test"},
        countdown_enabled=False,
        mappings=[
            {
                "id": "m",
                "trigger": "go",
                "action": {
                    "steps": [
                        {"type": "hold", "keys": ["a"], "duration_ms": 3000},
                        {"type": "press", "keys": ["b"]},
                    ]
                },
            }
        ],
    )
    try:
        listener.start(ConfigSnapshot(config, 1))
        await until(lambda: listener.state().output == "enabled")
        await client.callback("viewer", "go")
        assert await asyncio.to_thread(p.down.wait, 1)
        if stop:
            await listener.stop()
        else:
            client.task.cancel()
        await until(lambda: ("up", "a") in p.calls)
        assert p.calls == [("down", "a"), ("up", "a")]
        assert listener.state().output == "disabled"
    finally:
        await listener.stop()
        await k.close()


async def test_failsafe_during_hold_interrupts_and_releases_promptly():
    class FailSafeException(Exception):
        pass

    class Guarded(Port):
        def check_failsafe(self):
            if self.down.is_set():
                raise FailSafeException()

    p = Guarded()
    reports = []
    k = KeyboardExecutor(p, report=lambda *a: reports.append(a))
    k.enable(1)
    try:
        k.submit(
            action(
                k,
                [
                    {"type": "hold", "keys": ["a"], "duration_ms": 3000},
                    {"type": "press", "keys": ["b"]},
                ],
            )
        )
        await asyncio.wait_for(until(lambda: reports), 0.5)
        assert p.calls == [("down", "a"), ("up", "a")]
        assert reports[0][1]["code"] == "keyboard_failsafe"
        assert not k.submit(action(k, [{"type": "press", "keys": ["b"]}]))
    finally:
        await k.close()

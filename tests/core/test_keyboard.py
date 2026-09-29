import asyncio
import threading
from src.core.keyboard import KeyboardExecutor, KeyAction


async def test_queue_generation_expiry_and_serial_execution():
    entered = threading.Event()
    release = threading.Event()
    calls = []
    now = [0.0]

    class Port:
        def key_up(self, key):
            pass

        def key_down(self, key):
            keys = (key,)
            calls.append(keys)
            entered.set()
            release.wait(2)

    k = KeyboardExecutor(Port(), lambda: now[0], lambda *a: None)
    k.enable(1)
    k.submit(KeyAction(("a",), 1, 0))
    assert await asyncio.to_thread(entered.wait, 1)
    for _ in range(100):
        assert k.submit(KeyAction(("b",), 1, 0))
    assert not k.submit(KeyAction(("c",), 1, 0))
    k.disable()
    k.enable(2)
    now[0] = 2
    assert not k.submit(KeyAction(("o",), 1, 2))
    k.submit(KeyAction(("e",), 2, 0))
    release.set()
    await k.close(2)
    assert calls == [("a",)]


async def test_fault_disables_pending_keys():
    reports = []

    class Port:
        def key_up(self, key):
            pass

        def key_down(self, key):
            keys = (key,)
            raise RuntimeError("denied")

    k = KeyboardExecutor(Port(), report=lambda *a: reports.append(a))
    k.enable(1)
    k.submit(KeyAction(("a",), 1, k.clock()))
    for _ in range(100):
        if reports:
            break
        await asyncio.sleep(0.005)
    assert reports and not k.submit(KeyAction(("b",), 1, k.clock()))
    await k.close(1)


async def test_old_inflight_error_does_not_clear_new_generation():
    entered = threading.Event()
    release = threading.Event()
    calls = []

    class Port:
        def key_up(self, key):
            pass

        def key_down(self, key):
            keys = (key,)
            if keys == ("a",):
                entered.set()
                release.wait(2)
                raise RuntimeError("old error")
            calls.append(keys)

    k = KeyboardExecutor(Port())
    k.enable(1)
    k.submit(KeyAction(("a",), 1, k.clock()))
    assert await asyncio.to_thread(entered.wait, 1)
    k.disable()
    k.enable(2)
    k.submit(KeyAction(("b",), 2, k.clock()))
    release.set()
    for _ in range(100):
        if calls:
            break
        await asyncio.sleep(0.005)
    await k.close(1)
    assert calls == [("b",)]

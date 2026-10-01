import asyncio
from src.core.listener_service import ListenerService
from src.core.events import EventBus
from src.core.models import AppConfig, ConfigSnapshot


class Keyboard:
    def enable(self, g):
        pass

    def disable(self):
        pass

    def submit_reason(self, a, capacity=100):
        self.submit(a)

    def submit(self, a):
        pass


class Client:
    def __init__(self):
        self.disconnect_started = asyncio.Event()
        self.release = asyncio.Event()

    async def connect(self, cb):
        self.task = asyncio.create_task(asyncio.Event().wait())
        return self.task

    async def disconnect(self):
        self.disconnect_started.set()
        await self.release.wait()


async def settle():
    for _ in range(10):
        await asyncio.sleep(0)


async def test_repeated_stop_does_not_cancel_disconnect_cleanup():
    c = Client()
    s = ListenerService(lambda _: c, Keyboard(), EventBus("x"))
    s.start(ConfigSnapshot(AppConfig(tiktok={"channel":"a"}, countdown_enabled=False), 1))
    await settle()
    s.request_stop()
    await c.disconnect_started.wait()
    stop = asyncio.create_task(s.stop())
    await settle()
    try:
        assert not stop.done(), "Repeated Stop interrupted disconnect cleanup"
        assert s.state().status == "stopping"
    finally:
        c.release.set()
        await stop


async def test_late_keyboard_error_cannot_stop_new_session():
    clients = []

    def factory(_):
        c = Client()
        c.release.set()
        clients.append(c)
        return c

    s = ListenerService(factory, Keyboard(), EventBus("x"))
    snap = ConfigSnapshot(AppConfig(tiktok={"channel":"a"}, countdown_enabled=False), 1)
    s.start(snap)
    await settle()
    old = s.state().generation
    await s.stop()
    s.start(snap)
    await settle()
    try:
        s.keyboard_result(
            "error", {"code": "keyboard_error", "message": "old", "generation": old}
        )
        assert s.state().status == "connected"
    finally:
        await s.stop()

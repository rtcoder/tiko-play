import asyncio
import pytest
from src.core.listener_service import ListenerService
from src.core.models import AppConfig, ConfigSnapshot
from src.core.events import EventBus


class Keyboard:
    def __init__(self):
        self.actions = []
        self.enabled = False

    def enable(self, g):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def submit(self, a):
        if self.enabled:
            self.actions.append(a)


class Client:
    def __init__(self):
        self.ready = asyncio.Event()
        self.ready.set()
        self.callback = None
        self.task = None

    async def connect(self, callback):
        self.callback = callback
        await self.ready.wait()
        self.task = asyncio.create_task(asyncio.Event().wait())
        return self.task

    async def disconnect(self):
        if self.task:
            self.task.cancel()


async def settle():
    for _ in range(10):
        await asyncio.sleep(0)


async def test_single_start_stop_and_new_snapshot():
    clients = []
    k = Keyboard()

    def factory(name):
        c = Client()
        clients.append(c)
        return c

    s = ListenerService(factory, k, EventBus("x"))
    snap = ConfigSnapshot(
        AppConfig(
            streamer_id="alice",
            countdown_enabled=False,
            mappings=[{"id": "1", "trigger": "x", "keys": ["a"]}],
        ),
        1,
    )
    s.start(snap)
    s.start(snap)
    await settle()
    assert len(clients) == 1 and s.state().status == "connected"
    await clients[0].callback("u", "x")
    assert len(k.actions) == 1
    s.request_stop()
    await clients[0].callback("u", "x")
    await s.stop()
    assert len(k.actions) == 1 and s.state().status == "stopped" and not k.enabled
    s.start(snap)
    await settle()
    clients[-1].task.cancel()
    await settle()
    assert s.state().status == "error" and not k.enabled
    await s.stop()


async def test_stop_during_connect():
    c = Client()
    c.ready.clear()
    k = Keyboard()
    s = ListenerService(lambda _: c, k, EventBus("x"))
    s.start(ConfigSnapshot(AppConfig(streamer_id="a"), 1))
    await settle()
    await s.stop()
    assert s.state().status == "stopped" and not k.enabled


async def test_countdown_does_not_queue_comments():
    c = Client()
    k = Keyboard()
    gate = asyncio.Event()
    s = ListenerService(
        lambda _: c, k, EventBus("x"), sleep=lambda seconds: gate.wait()
    )
    s.start(
        ConfigSnapshot(
            AppConfig(
                streamer_id="a", mappings=[{"id": "1", "trigger": "x", "keys": ["a"]}]
            ),
            1,
        )
    )
    await settle()
    assert s.state().output == "countdown"
    await c.callback("u", "x")
    assert not k.actions
    gate.set()
    await settle()
    assert s.state().output == "enabled"
    assert not k.actions
    await c.callback("u", "x")
    assert len(k.actions) == 1
    await s.stop()

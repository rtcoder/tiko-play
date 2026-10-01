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

    def submit_reason(self, a, capacity=100):
        self.submit(a)

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
            tiktok={"channel":"alice"},
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
    s.start(ConfigSnapshot(AppConfig(tiktok={"channel":"a"}), 1))
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
                tiktok={"channel":"a"}, mappings=[{"id": "1", "trigger": "x", "keys": ["a"]}]
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


async def test_active_source_is_snapshot_and_old_callback_is_fenced():
    clients=[]; configs=[]; events=EventBus('x'); k=Keyboard()
    def factory(config):
        configs.append(config); client=Client(); clients.append(client); return client
    s=ListenerService(factory,k,events)
    config=AppConfig(platform='twitch',twitch={'channel':'alice','target_user':'BOB'},countdown_enabled=False,mappings=[{'id':'1','trigger':'x','keys':['a']}])
    s.start(ConfigSnapshot(config,1)); await settle()
    try:
        assert configs[0].platform=='twitch'
        assert s.state().active_platform=='twitch' and s.state().active_channel=='alice'
        await clients[0].callback('bob','x'); assert len(k.actions)==1
        payload=next(e['payload'] for e in events.recent() if e['type']=='comment')
        assert payload['platform']=='twitch' and payload['channel']=='alice'
        await s.stop(); s.start(ConfigSnapshot(config.model_copy(update={'platform':'tiktok','tiktok':AppConfig(tiktok={'channel':'new'}).tiktok}),2)); await settle()
        await clients[0].callback('bob','x'); assert len(k.actions)==1
        assert s.state().active_channel=='new'
        s.authorization_lost(); assert s.state().status=='connected'
    finally: await s.stop()


async def test_twitch_auth_loss_disables_before_cleanup_and_keeps_error():
    c=Client(); k=Keyboard(); s=ListenerService(lambda _:c,k,EventBus('x'))
    s.start(ConfigSnapshot(AppConfig(platform='twitch',twitch={'channel':'a'},countdown_enabled=False),1)); await settle()
    try:
        assert k.enabled
        s.authorization_lost()
        assert not k.enabled
        await settle()
        assert s.state().status=='error' and s.state().error['code']=='twitch_auth_required'
    finally: await s.stop()

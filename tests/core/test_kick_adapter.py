import asyncio
import json

import httpx
import pytest

from src.core.models import AppError


def frame(event, data=None, channel=None):
    return {"event": event, "data": json.dumps(data or {}), "channel": channel}


def message(
    id="m", channel="chatrooms.42.v2", room=42, event="App\\Events\\ChatMessageEvent"
):
    return frame(
        event,
        {
            "id": id,
            "chatroom_id": room,
            "sender": {"username": "Alice"},
            "content": "left",
        },
        channel,
    )


class Socket:
    def __init__(self, initial=()):
        self.queue = asyncio.Queue()
        self.sent = []
        self.closed = False
        for item in initial:
            self.queue.put_nowait(item)

    async def recv(self):
        item = await self.queue.get()
        if isinstance(item, Exception):
            raise item
        return json.dumps(item)

    async def send(self, value):
        self.sent.append(json.loads(value))
        if self.sent[-1]["event"] == "pusher:subscribe":
            self.queue.put_nowait(
                frame(
                    "pusher_internal:subscription_succeeded",
                    channel=self.sent[-1]["data"]["channel"],
                )
            )

    async def close(self):
        self.closed = True


async def setup(ws, response=None, room_id=None):
    from src.adapters.kick import KickAdapter

    calls = []

    def handler(req):
        calls.append(req)
        return response or httpx.Response(
            200, json={"slug": "alice", "chatroom": {"id": 42}}
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def connect(url, **kwargs):
        assert url.startswith("wss://ws-us2.pusher.com/app/")
        return ws

    return KickAdapter("alice", http, connect, chatroom_id=room_id), http, calls


def hello():
    return frame(
        "pusher:connection_established", {"socket_id": "1.2", "activity_timeout": 120}
    )


async def until(predicate):
    for _ in range(200):
        if predicate():
            return
        await asyncio.sleep(0)
    assert predicate()


async def test_kick_waits_for_subscription_and_delivers_only_selected_chat_once():
    ws = Socket([hello()])
    adapter, http, calls = await setup(ws)
    received = []

    async def callback(*args):
        received.append(args)

    try:
        child = await adapter.connect(callback)
        for item in [
            message(),
            message(event="App\\Events\\ChatMessageSentEvent", channel="chatrooms.42"),
            message("wrong", room=43),
            message("wrong2", channel="chatrooms.43.v2"),
            frame("pusher:ping"),
        ]:
            ws.queue.put_nowait(item)
        await until(lambda: any(x["event"] == "pusher:pong" for x in ws.sent))
        assert received == [("alice", "left")]
        assert calls[0].url.path == "/api/v2/channels/alice"
    finally:
        await adapter.disconnect()
        await http.aclose()
    assert ws.closed and child.done()


async def test_manual_chatroom_id_avoids_blocked_channel_lookup():
    ws = Socket([hello()])
    adapter, http, calls = await setup(ws, httpx.Response(403), room_id=42)
    try:
        await adapter.connect(None)
        assert calls == []
    finally:
        await adapter.disconnect()
        await http.aclose()


@pytest.mark.parametrize(
    "status,code",
    [
        (403, "kick_lookup_blocked"),
        (404, "streamer_not_found"),
        (429, "kick_rate_limited"),
    ],
)
async def test_kick_lookup_errors_are_actionable(status, code):
    adapter, http, _ = await setup(Socket(), httpx.Response(status))
    try:
        with pytest.raises(AppError) as caught:
            await adapter.connect(None)
        assert caught.value.code == code
    finally:
        await adapter.disconnect()
        await http.aclose()


async def test_disconnect_during_handshake_closes_socket():
    ws = Socket()
    adapter, http, _ = await setup(ws)
    task = asyncio.create_task(adapter.connect(None))
    await until(lambda: adapter._socket is not None)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert ws.closed
    await http.aclose()


async def test_broken_socket_and_protocol_stop_listener_without_raw_exception():
    for event in [
        EOFError("private details"),
        frame("pusher:error", {"message": "private details"}),
        message(id=None),
    ]:
        ws = Socket([hello()])
        adapter, http, _ = await setup(ws)
        try:
            child = await adapter.connect(None)
            ws.queue.put_nowait(event)
            with pytest.raises(AppError) as caught:
                await asyncio.wait_for(child, 1)
            assert "private details" not in str(caught.value)
        finally:
            await adapter.disconnect()
            await http.aclose()

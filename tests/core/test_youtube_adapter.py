import asyncio
from datetime import UTC, datetime

import httpx
import pytest

from src.core.models import AppError


class Key:
    async def load(self):
        return "PRIVATE_KEY"


class Stream:
    def __init__(self, *pages):
        self.queue = asyncio.Queue()
        self.closed = False
        for page in pages:
            self.queue.put_nowait(page)

    async def read(self):
        page = await self.queue.get()
        if isinstance(page, Exception):
            raise page
        return page

    async def close(self):
        self.closed = True


def message(id="m", user="UCViewer", text="left", kind=1):
    return {
        "id": id,
        "snippet": {
            "type": kind,
            "liveChatId": "chat",
            "publishedAt": datetime.now(UTC).isoformat(),
            "textMessageDetails": {"messageText": text},
        },
        "authorDetails": {"channelId": user, "displayName": "Not a unique login"},
    }


async def setup(stream, response=None):
    from src.adapters.youtube import YouTubeAdapter

    calls = []

    def handler(request):
        calls.append(request)
        return response or httpx.Response(
            200,
            json={"items": [{"liveStreamingDetails": {"activeLiveChatId": "chat"}}]},
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    async def open_stream(chat, key):
        assert chat == "chat" and key == "PRIVATE_KEY"
        return stream

    return (
        YouTubeAdapter("abcdefghijk", Key(), http, open_stream=open_stream),
        http,
        calls,
    )


async def until(predicate):
    for _ in range(200):
        if predicate():
            return
        await asyncio.sleep(0)
    assert predicate()


async def test_youtube_skips_initial_history_deduplicates_and_uses_stable_identity():
    stream = Stream({"items": [message("old")], "nextPageToken": "next"})
    adapter, http, calls = await setup(stream)
    received = []

    async def callback(*args):
        received.append(args)

    try:
        child = await adapter.connect(callback)
        assert received == []
        stream.queue.put_nowait(
            {"items": [message("old"), message(), message(), message("gift", kind=15)]}
        )
        await until(lambda: len(received) == 1)
        assert received == [("UCViewer", "left")]
        assert calls[0].url.params["id"] == "abcdefghijk"
        assert calls[0].headers["x-goog-api-key"] == "PRIVATE_KEY"
        assert "PRIVATE_KEY" not in str(calls[0].url)
    finally:
        await adapter.disconnect()
        await http.aclose()
    assert stream.closed and child.done()


@pytest.mark.parametrize(
    "response,code",
    [
        (httpx.Response(200, json={"items": []}), "streamer_not_found"),
        (
            httpx.Response(200, json={"items": [{"liveStreamingDetails": {}}]}),
            "youtube_chat_unavailable",
        ),
        (
            httpx.Response(
                403, json={"error": {"errors": [{"reason": "quotaExceeded"}]}}
            ),
            "youtube_quota_exceeded",
        ),
        (
            httpx.Response(400, json={"error": {"errors": [{"reason": "keyInvalid"}]}}),
            "youtube_key_invalid",
        ),
    ],
)
async def test_youtube_errors_do_not_expose_key(response, code):
    adapter, http, _ = await setup(Stream(), response)
    try:
        with pytest.raises(AppError) as caught:
            await adapter.connect(None)
        assert caught.value.code == code
        assert "PRIVATE_KEY" not in str(caught.value)
    finally:
        await adapter.disconnect()
        await http.aclose()


async def test_youtube_stream_end_propagates_and_stop_closes_partial_connection():
    for ending in ({"offlineAt": "2026-01-01"}, {"items": [message(kind=4)]}):
        stream = Stream({"items": []}, ending)
        adapter, http, _ = await setup(stream)
        try:
            child = await adapter.connect(None)
            with pytest.raises(AppError) as caught:
                await asyncio.wait_for(child, 1)
            assert caught.value.code == "youtube_chat_ended"
        finally:
            await adapter.disconnect()
            await http.aclose()
    stream = Stream()
    adapter, http, _ = await setup(stream)
    task = asyncio.create_task(adapter.connect(None))
    await until(lambda: adapter._stream is not None)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert stream.closed
    await http.aclose()


async def test_delayed_history_batch_never_runs_old_commands():
    from datetime import datetime

    old = message("delayed-old")
    old["snippet"]["publishedAt"] = "2000-01-01T00:00:00Z"
    recent = message("fresh")
    recent["snippet"]["publishedAt"] = datetime.now(UTC).isoformat()
    stream = Stream({"items": []})
    adapter, http, _ = await setup(stream)
    received = []

    async def callback(*args):
        received.append(args)

    try:
        await adapter.connect(callback)
        recent["snippet"]["publishedAt"] = datetime.now(UTC).isoformat()
        stream.queue.put_nowait({"items": [old, recent]})
        await until(lambda: stream.queue.empty())
        assert received == [("UCViewer", "left")]
    finally:
        await adapter.disconnect()
        await http.aclose()

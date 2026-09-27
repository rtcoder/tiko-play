"""YouTube public live chat via the official API and streaming gRPC."""

import asyncio
from contextlib import suppress
from datetime import UTC, datetime

from src.adapters.twitch_protocol import SeenMessages
from src.core.models import AppError


def ended():
    return AppError(
        "youtube_chat_ended", "Transmisja lub czat YouTube zostały zakończone."
    )


def protocol_error():
    return AppError(
        "youtube_protocol_error",
        "Niepoprawna odpowiedź czatu YouTube. Uruchom nasłuch ponownie.",
    )


class YouTubeAdapter:
    def __init__(self, channel, key_store, http, *, open_stream=None):
        self.channel, self.key_store, self.http = channel, key_store, http
        self.open_stream = open_stream
        self._stream = self._child = None
        self._stopped = False
        self._seen = SeenMessages()
        self._chat_id = None

    async def connect(self, on_comment):
        self._started_at = datetime.now(UTC)
        try:
            key = await self.key_store.load() if self.key_store else None
            if not key:
                raise AppError(
                    "youtube_key_required",
                    "Zapisz klucz YouTube Data API przed rozpoczęciem nasłuchu.",
                )
            response = await self.http.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "liveStreamingDetails", "id": self.channel},
                headers={"X-Goog-Api-Key": key},
                timeout=10,
            )
            if response.status_code != 200:
                try:
                    reasons = {
                        e.get("reason")
                        for e in response.json().get("error", {}).get("errors", [])
                    }
                except (TypeError, ValueError, AttributeError):
                    reasons = set()
                if (
                    reasons
                    & {"quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded"}
                    or response.status_code == 429
                ):
                    raise AppError(
                        "youtube_quota_exceeded",
                        "Limit YouTube API został wyczerpany. Sprawdź limit projektu Google Cloud lub spróbuj później.",
                    )
                if reasons & {
                    "keyInvalid",
                    "accessNotConfigured",
                    "ipRefererBlocked",
                    "forbidden",
                } or response.status_code in (400, 401, 403):
                    raise AppError(
                        "youtube_key_invalid",
                        "Sprawdź klucz, ograniczenia klucza i włączenie YouTube Data API v3 w Google Cloud.",
                    )
                raise AppError(
                    "connection_error", "YouTube jest niedostępny. Spróbuj ponownie."
                )
            items = response.json()["items"]
            if not items:
                raise AppError(
                    "streamer_not_found", "Nie znaleziono transmisji YouTube."
                )
            self._chat_id = (
                items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")
            )
            if not isinstance(self._chat_id, str) or not self._chat_id:
                raise AppError(
                    "youtube_chat_unavailable",
                    "Ta transmisja nie ma aktywnego czatu YouTube. Sprawdź link i czy LIVE już trwa.",
                )
            if self.open_stream is None:
                from src.adapters.youtube_stream import open_youtube_stream

                self.open_stream = open_youtube_stream
            self._stream = await self.open_stream(self._chat_id, key)
            first = await asyncio.wait_for(self._stream.read(), 15)
            # First batch is recent history, never commands for the current game.
            await self._page(first, on_comment, history=True)
            self._child = asyncio.create_task(self._run(on_comment))
            return self._child
        except BaseException as exc:
            await self.disconnect()
            if isinstance(exc, (asyncio.CancelledError, AppError)):
                raise
            raise AppError(
                "connection_error",
                "Nie można połączyć się z YouTube. Sprawdź transmisję i sieć.",
            ) from None

    async def _page(self, page, callback, *, history=False):
        if not isinstance(page, dict):
            raise protocol_error()
        if page.get("offlineAt"):
            raise ended()
        items = page.get("items", [])
        if not isinstance(items, list):
            raise protocol_error()
        for item in items:
            try:
                snippet = item["snippet"]
                kind = snippet["type"]
                if kind == 4:
                    raise ended()
                if kind != 1:
                    continue
                if snippet.get("liveChatId") != self._chat_id:
                    continue
                published = datetime.fromisoformat(snippet["publishedAt"])
                if published.tzinfo is None:
                    raise ValueError()
                if not history and published <= self._started_at:
                    continue
                mid = item["id"]
                user = item["authorDetails"]["channelId"]
                text = snippet["textMessageDetails"]["messageText"]
                if not all(
                    isinstance(x, str) and x for x in (mid, user)
                ) or not isinstance(text, str):
                    raise ValueError()
            except (KeyError, TypeError, ValueError):
                raise protocol_error() from None
            if self._seen.accept(mid, mid) and not history and not self._stopped:
                await callback(user, text)

    async def _run(self, callback):
        try:
            while not self._stopped:
                page = await self._stream.read()
                await self._page(page, callback)
        except asyncio.CancelledError:
            raise
        except AppError:
            raise
        except Exception:  # noqa: BLE001 — never expose API keys in transport errors
            raise AppError(
                "connection_lost",
                "Połączenie z YouTube zostało przerwane. Uruchom nasłuch ponownie.",
            ) from None

    async def disconnect(self):
        self._stopped = True
        if self._child and self._child is not asyncio.current_task():
            self._child.cancel()
            await asyncio.gather(self._child, return_exceptions=True)
        stream, self._stream = self._stream, None
        if stream:
            with suppress(Exception):
                await asyncio.wait_for(stream.close(), 1)

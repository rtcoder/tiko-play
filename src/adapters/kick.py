"""Anonymous, unofficial Kick/Pusher chat. No webhook or relay is used."""

import asyncio
import json
from contextlib import suppress

from src.adapters.twitch_protocol import SeenMessages
from src.core.models import AppError

WS = "wss://ws-us2.pusher.com/app/32cbd69e4b950bf97679?protocol=7&client=js&version=8.4.0&flash=false"
CHAT_EVENTS = {"App\\Events\\ChatMessageEvent", "App\\Events\\ChatMessageSentEvent"}


def protocol_error():
    return AppError(
        "kick_protocol_error",
        "Zmienił się format czatu Kicka. Integracja nieoficjalna wymaga aktualizacji.",
    )


class KickAdapter:
    def __init__(self, channel, http, ws_connect, *, chatroom_id=None):
        self.channel, self.http, self.ws_connect = channel, http, ws_connect
        self.chatroom_id = chatroom_id
        self._socket = self._child = None
        self._stopped = False
        self._timeout = 120
        self._channels = set()
        self._seen = SeenMessages()

    async def _receive(self, timeout):
        raw = await asyncio.wait_for(self._socket.recv(), timeout)
        try:
            frame = json.loads(raw)
            if not isinstance(frame, dict) or not isinstance(frame.get("event"), str):
                raise TypeError()
            data = frame.get("data", {})
            frame["data"] = json.loads(data) if isinstance(data, str) else data
            if not isinstance(frame["data"], dict):
                raise TypeError()
            if frame["event"] in (
                "pusher:error",
                "pusher:subscription_error",
                "pusher_internal:subscription_error",
            ):
                raise protocol_error()
            return frame
        except (ValueError, TypeError):
            raise protocol_error() from None

    async def _send(self, event, data=None):
        await self._socket.send(json.dumps({"event": event, "data": data or {}}))

    async def connect(self, on_comment):
        try:
            if self.chatroom_id is None:
                response = await self.http.get(
                    "https://kick.com/api/v2/channels/" + self.channel,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "TikoPlay/2.0",
                    },
                    timeout=10,
                )
                if response.status_code in (401, 403):
                    raise AppError(
                        "kick_lookup_blocked",
                        "Kick zablokował odczyt kanału. Wpisz opcjonalne ID pokoju czatu w ustawieniach Kicka.",
                    )
                if response.status_code == 404:
                    raise AppError("streamer_not_found", "Nie znaleziono kanału Kick.")
                if response.status_code == 429:
                    raise AppError(
                        "kick_rate_limited",
                        "Kick ograniczył liczbę połączeń. Spróbuj później.",
                    )
                response.raise_for_status()
                self.chatroom_id = response.json()["chatroom"]["id"]
            if type(self.chatroom_id) is not int or self.chatroom_id <= 0:
                raise protocol_error()
            self._channels = {
                f"chatrooms.{self.chatroom_id}.v2",
                f"chatrooms.{self.chatroom_id}",
            }
            self._socket = await self.ws_connect(
                WS,
                open_timeout=10,
                close_timeout=1,
                max_size=1024 * 1024,
                max_queue=32,
                ping_interval=None,
                origin="https://kick.com",
            )
            async with asyncio.timeout(10):
                hello = await self._receive(10)
                if hello["event"] != "pusher:connection_established":
                    raise protocol_error()
                self._timeout = float(hello["data"]["activity_timeout"])
                if not 0 < self._timeout <= 600:
                    raise protocol_error()
                for channel in sorted(self._channels):
                    await self._send(
                        "pusher:subscribe", {"auth": "", "channel": channel}
                    )
                subscribed = set()
                while subscribed != self._channels:
                    frame = await self._receive(10)
                    if (
                        frame["event"] == "pusher_internal:subscription_succeeded"
                        and frame.get("channel") in self._channels
                    ):
                        subscribed.add(frame["channel"])
                    elif frame["event"] == "pusher:ping":
                        await self._send("pusher:pong")
                    # No keystrokes from messages received before setup completes.
            self._child = asyncio.create_task(self._run(on_comment))
            return self._child
        except BaseException as exc:
            await self.disconnect()
            if isinstance(exc, (asyncio.CancelledError, AppError)):
                raise
            raise AppError(
                "connection_error",
                "Nie można połączyć się z czatem Kicka. Sprawdź kanał i sieć.",
            ) from None

    async def _run(self, callback):
        try:
            while not self._stopped:
                try:
                    frame = await self._receive(self._timeout)
                except TimeoutError:
                    await self._send("pusher:ping")
                    frame = await self._receive(10)
                if frame["event"] == "pusher:ping":
                    await self._send("pusher:pong")
                elif (
                    frame["event"] in CHAT_EVENTS
                    and frame.get("channel") in self._channels
                ):
                    data = frame["data"]
                    if data.get("chatroom_id") != self.chatroom_id:
                        continue
                    mid, user, text = (
                        data["id"],
                        data["sender"]["username"],
                        data["content"],
                    )
                    if not all(
                        isinstance(x, str) and x for x in (mid, user)
                    ) or not isinstance(text, str):
                        raise protocol_error()
                    if self._seen.accept(mid, mid) and not self._stopped:
                        await callback(user.lower(), text)
        except asyncio.CancelledError:
            raise
        except AppError:
            raise
        except (KeyError, TypeError, ValueError):
            raise protocol_error() from None
        except Exception:  # noqa: BLE001 — keep third-party transport details out of UI
            raise AppError(
                "connection_lost",
                "Połączenie z Kickiem zostało przerwane. Uruchom nasłuch ponownie.",
            ) from None

    async def disconnect(self):
        self._stopped = True
        if self._child and self._child is not asyncio.current_task():
            self._child.cancel()
            await asyncio.gather(self._child, return_exceptions=True)
        ws, self._socket = self._socket, None
        if ws:
            with suppress(Exception):
                await asyncio.wait_for(ws.close(), 1)

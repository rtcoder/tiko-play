import asyncio
from typing import Awaitable, Callable, Protocol

CommentHandler = Callable[[str, str], Awaitable[None]]


class ChatAdapter(Protocol):
    async def connect(self, on_comment: CommentHandler) -> asyncio.Task[None]: ...
    async def disconnect(self) -> None: ...


class ChatAdapterFactory:
    def __init__(self, auth, http, ws_connect):
        self.auth, self.http, self.ws_connect = auth, http, ws_connect

    def __call__(self, config) -> ChatAdapter:
        if config.platform == "tiktok":
            from src.adapters.tiktok import TikTokAdapter

            return TikTokAdapter(config.tiktok.channel)
        from src.adapters.twitch import TwitchAdapter

        return TwitchAdapter(
            config.twitch.channel, self.auth, self.http, self.ws_connect
        )

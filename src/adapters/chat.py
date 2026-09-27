import asyncio
from typing import Awaitable, Callable, Protocol

CommentHandler = Callable[[str, str], Awaitable[None]]


class ChatAdapter(Protocol):
    async def connect(self, on_comment: CommentHandler) -> asyncio.Task[None]: ...
    async def disconnect(self) -> None: ...


class ChatAdapterFactory:
    def __init__(self, auth, http, ws_connect, *, youtube_keys=None):
        self.auth, self.http, self.ws_connect = auth, http, ws_connect
        self.youtube_keys = youtube_keys

    def __call__(self, config) -> ChatAdapter:
        if config.platform == "tiktok":
            from src.adapters.tiktok import TikTokAdapter

            return TikTokAdapter(config.tiktok.channel)
        if config.platform == "youtube":
            from src.adapters.youtube import YouTubeAdapter

            return YouTubeAdapter(config.youtube.channel, self.youtube_keys, self.http)
        if config.platform == "kick":
            from src.adapters.kick import KickAdapter

            return KickAdapter(
                config.kick.channel,
                self.http,
                self.ws_connect,
                chatroom_id=config.kick.chatroom_id,
            )
        from src.adapters.twitch import TwitchAdapter

        return TwitchAdapter(
            config.twitch.channel, self.auth, self.http, self.ws_connect
        )

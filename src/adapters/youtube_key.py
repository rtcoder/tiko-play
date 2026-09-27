"""YouTube API key lives only in the native vault, never in config or events."""

import asyncio

from src.adapters.twitch_credentials import NativeCredentialStore


class YouTubeKeyStore(NativeCredentialStore):
    SERVICE = "TikoPlay.YouTube"
    ACCOUNT = "api-key"

    def __init__(self, *, backend=None):
        super().__init__(backend=backend)
        self.lock = asyncio.Lock()

    async def load(self):
        return await self._io(
            lambda: self.native_backend().get_password(self.SERVICE, self.ACCOUNT)
        )

    async def save(self, value):
        await self._io(
            lambda: self.native_backend().set_password(
                self.SERVICE, self.ACCOUNT, value
            )
        )

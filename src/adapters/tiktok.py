from src.core.models import AppError


class TikTokAdapter:
    def __init__(self, streamer_id):
        self.streamer_id = streamer_id
        self.client = None

    async def connect(self, on_comment):
        from TikTokLive import TikTokLiveClient
        from TikTokLive.events import CommentEvent

        self.client = TikTokLiveClient(unique_id=self.streamer_id)

        @self.client.on(CommentEvent)
        async def comment(event):
            await on_comment(event.user.unique_id, event.comment)

        try:
            return await self.client.start()
        except Exception as exc:
            messages = {
                "UserOfflineError": ("streamer_offline", "Streamer jest offline."),
                "UserNotFoundError": (
                    "streamer_not_found",
                    "Nie znaleziono streamera.",
                ),
                "AlreadyConnectedError": (
                    "already_connected",
                    "Klient jest już połączony.",
                ),
            }
            code, message = messages.get(
                type(exc).__name__,
                (
                    "connection_error",
                    "Nie można połączyć się z TikTokiem. Sprawdź sieć i nick.",
                ),
            )
            raise AppError(code, message) from exc

    async def disconnect(self):
        if self.client:
            await self.client.disconnect()

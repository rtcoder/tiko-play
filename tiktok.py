from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import UserNotFoundError
from TikTokLive.events import CommentEvent
import pyautogui
import threading

class TikTokListener:
    def __init__(self):
        self.streamer_id = ""
        self.allowed_keys = []
        self.target_user = ""
        self.client = None
        self.running = False
        self.thread = None

    def configure(self, streamer_id, keys, target_user):
        self.streamer_id = streamer_id
        self.allowed_keys = keys
        self.target_user = target_user

    def start(self):
        if not self.streamer_id or self.running:
            return

        def run():
            self.client = TikTokLiveClient(unique_id=self.streamer_id)

            @self.client.on(CommentEvent)
            async def on_comment(event: CommentEvent):
                if self.target_user and event.user.unique_id != self.target_user:
                    return
                if event.comment in self.allowed_keys:
                    pyautogui.press(event.comment)

            self.running = True

            try:
                self.client.run()
            except UserNotFoundError:
                print("brak streamera")
                self.running = False

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.client:
            self.client.stop()
        self.running = False
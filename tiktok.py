import threading

import pyautogui
from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import UserNotFoundError
from TikTokLive.events import CommentEvent


class TikTokListener:
    def __init__(self):
        self.streamer_id = ""
        self.target_user = ""
        self.mappings = {}
        self.client = None
        self.running = False
        self.thread = None

    def configure(self, settings):
        self.streamer_id = settings.get("streamer_id", "")
        self.target_user = settings.get("target_user", "")
        self.mappings = settings.get("mappings", {})

    def start(self):
        if not self.streamer_id or self.running:
            return

        def run():
            self.client = TikTokLiveClient(unique_id=self.streamer_id)

            @self.client.on(CommentEvent)
            async def on_comment(event: CommentEvent):
                if self.target_user and event.user.unique_id != self.target_user:
                    return
                comment = event.comment.strip().lower()
                print(f"Komentarz: {comment}")
                if comment in self.mappings:
                    keys = self.mappings[comment]
                    if len(keys) == 1:
                        pyautogui.press(keys[0])
                    else:
                        pyautogui.hotkey(*keys)

            self.running = True
            try:
                self.client.run()
            except UserNotFoundError:
                print("Nie znaleziono streamera")
                self.running = False

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.client:
            self.client.stop()
        self.running = False

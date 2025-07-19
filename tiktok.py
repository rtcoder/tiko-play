from TikTokLive import TikTokLiveClient
from TikTokLive.client.errors import UserNotFoundError
from TikTokLive.events import CommentEvent
import pyautogui
import threading

class TikTokListener:
    def __init__(self):
        self.streamer_id = ""
        self.key_mapping = {}
        self.target_user = ""
        self.client = None
        self.running = False
        self.thread = None

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
                if comment in self.key_mapping:
                    key = self.key_mapping[comment]
                    print(f"🟢 Komentarz '{comment}' → uruchamiam klawisz '{key}'")
                    pyautogui.press(key)
                else:
                    print(f"⚪ Nieobsługiwany komentarz: '{comment}'")

            self.running = True
            try:
                self.client.run()
            except UserNotFoundError:
                print("❌ Nie znaleziono streamera.")
            self.running = False

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        if self.client:
            self.client.stop()
        self.running = False

import asyncio
import time
import pyautogui
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent

class TikTokListener:
    def __init__(self, logger=None):
        self.client = None
        self.running = False
        self.task = None
        self.cooldowns = {}
        self.logger = logger

    async def start(self, config):
        if self.running:
            return

        self.running = True
        streamer = config["streamer_id"]
        target_user = config.get("target_user")
        mappings = {
            m["trigger"].lower(): m["keys"]
            for m in config.get("mappings", [])
        }

        self.log(f"🔌 Łączenie z @{streamer}")
        self.client = TikTokLiveClient(unique_id=streamer)

        @self.client.on(CommentEvent)
        async def on_comment(event: CommentEvent):
            if not self.running:
                return

            comment = event.comment.strip().lower()
            user = event.user.unique_id

            self.log(f"💬 {user}: {comment}")

            if target_user and user != target_user:
                return

            if comment not in mappings:
                return

            # cooldown per trigger
            now = time.time()
            last = self.cooldowns.get(comment, 0)
            if now - last < 0.3:
                return
            self.cooldowns[comment] = now

            keys = mappings[comment]
            self.log(f"🎮 Trigger '{comment}' → {keys}")
            print(f"Trigger '{comment}' -> {keys}")

            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)

        await self.client.start()

        while self.running:
            await asyncio.sleep(0.1)

        await self.client.disconnect()

    def stop(self):
        self.running = False
        self.log("⏹ Listener zatrzymany")

    def log(self, msg):
        if self.logger:
            self.logger.log(msg)


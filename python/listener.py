import sys
import asyncio
import signal
import pyautogui
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent
from config import load_config

running = True

def shutdown(sig, frame):
    global running
    running = False

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

config_path = sys.argv[1]
config = load_config(config_path)

STREAMER = config["streamer_id"]
TARGET = config.get("target_user")
MAPPINGS = {
    m["trigger"]: m["keys"]
    for m in config["mappings"]
}

client = TikTokLiveClient(unique_id=STREAMER)

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    if not running:
        await client.disconnect()
        sys.exit(0)

    if TARGET and event.user.unique_id != TARGET:
        return

    msg = event.comment.strip().lower()

    if msg in MAPPINGS:
        keys = MAPPINGS[msg]
        print(f"Trigger: {msg} -> {keys}")

        if len(keys) == 1:
            pyautogui.press(keys[0])
        else:
            pyautogui.hotkey(*keys)

async def main():
    await client.start()
    while running:
        await asyncio.sleep(0.1)
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

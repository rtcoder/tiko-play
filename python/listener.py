import asyncio
import signal
import sys
from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent

running = True

def shutdown(sig, frame):
    global running
    print("Shutting down listener...")
    running = False

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

client = TikTokLiveClient(unique_id="@retrourysta")

@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    if not running:
        await client.disconnect()
        sys.exit(0)

    print(f"{event.user.nickname}: {event.comment}")

async def main():
    await client.start()
    while running:
        await asyncio.sleep(0.1)

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())

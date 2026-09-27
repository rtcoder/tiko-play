import asyncio
from contextlib import suppress
from starlette.websockets import WebSocketDisconnect

async def stream_events(ws,events,state):
    await ws.accept()
    sub=events.subscribe()
    snapshot={'type':'snapshot','state':state(),'events':events.recent(),'watermark':events.sequence,'instance_id':events.instance_id}
    async def send():
        await ws.send_json(snapshot)
        while not sub.closed:
            event=await sub.queue.get()
            if event['id']>snapshot['watermark']:await ws.send_json(event)
    async def receive():
        while True:await ws.receive_text()
    tasks=[asyncio.create_task(send()),asyncio.create_task(receive()),asyncio.create_task(sub.ended.wait())]
    try:
        done,_=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            with suppress(WebSocketDisconnect):task.result()
        if sub.closed:
            with suppress(RuntimeError):await ws.close(code=1013)
    finally:
        events.unsubscribe(sub)
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)

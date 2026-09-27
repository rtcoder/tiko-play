import asyncio
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from copy import deepcopy


@dataclass(eq=False)
class Subscription:
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(200))
    closed: bool = False
    ended: asyncio.Event = field(default_factory=asyncio.Event)


class EventBus:
    def __init__(self, instance_id):
        self.instance_id = instance_id
        self.sequence = 0
        self.buffer = deque(maxlen=1000)
        self.subscribers = set()

    def publish(self, type, payload):
        payload = deepcopy(payload)
        if type == "comment":
            payload["comment"] = str(payload.get("comment", ""))[:2000]
        self.sequence += 1
        event = dict(
            id=self.sequence,
            instance_id=self.instance_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            type=type,
            payload=payload,
        )
        self.buffer.append(event)
        for sub in tuple(self.subscribers):
            try:
                sub.queue.put_nowait(event)
            except asyncio.QueueFull:
                self.unsubscribe(sub)
        return event

    def recent(self):
        return list(self.buffer)

    def subscribe(self):
        sub = Subscription()
        self.subscribers.add(sub)
        return sub

    def unsubscribe(self, sub):
        self.subscribers.discard(sub)
        sub.closed = True
        sub.ended.set()

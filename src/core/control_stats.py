"""Bounded session diagnostics; publication is owned by the asyncio listener."""

from collections import Counter, deque


class ControlStats:
    def __init__(self):
        self.counts = Counter()
        self.recent = deque(maxlen=30)
        self.sequence = 0

    def record(self, reason, actor_id="", comment="", mapping_id=""):
        self.counts[reason] += 1
        self.sequence += 1
        self.recent.append(
            {
                "id": self.sequence,
                "reason": reason,
                "actor_id": actor_id[:128],
                "comment": comment[:200],
                "mapping_id": mapping_id,
            }
        )

    def snapshot(self):
        return {"counts": dict(self.counts), "recent": list(self.recent)}

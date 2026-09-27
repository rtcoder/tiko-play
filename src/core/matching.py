import time
from src.core.models import AppConfig


def normalize_trigger(text: str) -> str:
    return text.strip().lower()


class Matcher:
    def __init__(self, config: AppConfig, clock=time.monotonic):
        self.target = config.target_user
        self.rules = {m.trigger: m.keys for m in config.mappings}
        self.clock = clock
        self.last = {}

    def match(self, user_id: str, comment: str):
        if self.target and self.target != user_id:
            return None
        trigger = normalize_trigger(comment)
        keys = self.rules.get(trigger)
        if keys is None:
            return None
        now = self.clock()
        if trigger in self.last and now - self.last[trigger] < 0.3:
            return None
        self.last[trigger] = now
        return keys

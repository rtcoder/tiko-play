import time
from src.core.models import AppConfig
from src.core.users import allowed_users


def normalize_trigger(text: str) -> str:
    return text.strip().lower()


class Matcher:
    def __init__(self, config: AppConfig, clock=time.monotonic):
        self.fold_users = config.platform in ("twitch", "kick")
        self.targets = allowed_users(config.active_source().target_user)
        if self.fold_users:
            self.targets = frozenset(u.lower() for u in self.targets)
        self.rules = {m.trigger: m.keys for m in config.mappings}
        self.clock = clock
        self.last = {}

    def match(self, user_id: str, comment: str):
        if self.fold_users:
            user_id = user_id.lower()
        if self.targets and user_id not in self.targets:
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

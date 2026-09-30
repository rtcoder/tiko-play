import time
from dataclasses import dataclass, replace
from typing import Literal

from src.core.models import AppConfig, Mapping
from src.core.output_policy import ACTION_COOLDOWN_SECONDS
from src.core.users import allowed_users


def normalize_trigger(text: str) -> str:
    return text.strip().lower()


@dataclass(frozen=True)
class MatchDecision:
    actor_id: str
    trigger: str
    reason: Literal["matched", "user_filtered", "no_mapping", "action_cooldown"]
    mapping: Mapping | None = None

    @property
    def mapping_id(self):
        return self.mapping.id if self.mapping is not None else None


class Matcher:
    def __init__(
        self,
        config: AppConfig,
        clock=time.monotonic,
        *,
        cooldown=ACTION_COOLDOWN_SECONDS,
    ):
        self.fold_users = config.platform in ("twitch", "kick")
        self.targets = allowed_users(config.active_source().target_user)
        if self.fold_users:
            self.targets = frozenset(u.lower() for u in self.targets)
        self.rules = {m.trigger: m for m in config.mappings}
        self.clock = clock
        # The duration uses the same unit as the injected clock.
        self.cooldown = cooldown
        self.last = {}

    def match(self, user_id: str, comment: str):
        mapping = self.match_mapping(user_id, comment)
        return mapping.keys if mapping is not None else None

    def resolve(self, user_id: str, comment: str) -> MatchDecision:
        actor_id = user_id.lower() if self.fold_users else user_id
        trigger = normalize_trigger(comment)
        if self.targets and actor_id not in self.targets:
            return MatchDecision(actor_id, trigger, "user_filtered")
        mapping = self.rules.get(trigger)
        return MatchDecision(
            actor_id, trigger, "matched" if mapping else "no_mapping", mapping
        )

    def decide(self, user_id: str, comment: str) -> MatchDecision:
        decision = self.resolve(user_id, comment)
        if decision.reason != "matched":
            return decision
        now = self.clock()
        if (
            decision.trigger in self.last
            and now - self.last[decision.trigger] < self.cooldown
        ):
            return replace(decision, reason="action_cooldown")
        self.last[decision.trigger] = now
        return decision

    def match_mapping(self, user_id: str, comment: str):
        decision = self.decide(user_id, comment)
        return decision.mapping if decision.reason == "matched" else None

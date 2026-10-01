"""Session-owned admission limits. check is read-only; commit only after admission."""

from collections import OrderedDict
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class ControlLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    action_cooldown_ms: int = Field(default=300, strict=True, ge=0, le=60000)
    viewer_cooldown_ms: int = Field(default=0, strict=True, ge=0, le=60000)
    queue_capacity: int = Field(default=100, strict=True, ge=1, le=100)
    action_ttl_ms: int = Field(default=1000, strict=True, ge=100, le=5000)


@dataclass(frozen=True)
class LimitDecision:
    reason: str | None = None


class RateLimiter:
    def __init__(self, limits: ControlLimits):
        self.limits = limits
        self.viewers = OrderedDict()
        self.actions = {}

    def check(self, actor_id: str, mapping_id: str, now: float) -> LimitDecision:
        # Integer milliseconds for both LIVE and simulation avoid float boundaries.
        tick = round(now * 1000)
        viewer = self.viewers.get(actor_id)
        if viewer is not None and tick < viewer + self.limits.viewer_cooldown_ms:
            return LimitDecision("user_cooldown")
        action = self.actions.get(mapping_id)
        if action is not None and tick < action + self.limits.action_cooldown_ms:
            return LimitDecision("action_cooldown")
        return LimitDecision()

    def commit(self, actor_id: str, mapping_id: str, now: float):
        tick = round(now * 1000)
        self.prune(now)
        if self.limits.viewer_cooldown_ms:
            self.viewers[actor_id] = tick
            self.viewers.move_to_end(actor_id)
            if len(self.viewers) > 10000:
                self.viewers.popitem(last=False)
        self.actions[mapping_id] = tick

    def prune(self, now: float):
        tick = round(now * 1000)
        while self.viewers and next(iter(self.viewers.values())) <= tick - 120000:
            self.viewers.popitem(last=False)

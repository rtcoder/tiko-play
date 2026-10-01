"""Pure virtual output. No chat adapters, keyboard ports, threads, or wall-clock waits."""

from collections import deque
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.core.actions import ActionDefinition
from src.core.matching import Matcher
from src.core.models import AppError, ConfigSnapshot, Platform
from src.core.output_policy import (
    action_expired,
    queue_has_capacity,
)
from src.core.rate_limits import ControlLimits, RateLimiter


class SimulationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    offset_ms: int = Field(strict=True, ge=0, le=60000)
    user_id: str = Field(min_length=1, max_length=128)
    comment: str = Field(max_length=2000)


class SimulationScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    messages: tuple[SimulationMessage, ...] = Field(min_length=1, max_length=1000)


class SimulationRequest(SimulationScenario):
    expected_revision: int = Field(strict=True, ge=1)
    profile_id: str | None = Field(default=None, min_length=1, max_length=128)
    platform: Platform | None = None


class SimulationStep(BaseModel):
    model_config = ConfigDict(frozen=True)
    type: Literal["press", "hold", "wait"]
    keys: tuple[str, ...] = ()
    start_ms: int
    end_ms: int
    duration_ms: int


class SimulationDecision(BaseModel):
    model_config = ConfigDict(frozen=True)
    message_index: int
    offset_ms: int
    user_id: str
    actor_id: str
    comment: str
    trigger: str
    mapping_id: str | None
    reason: Literal[
        "planned",
        "user_filtered",
        "no_mapping",
        "action_cooldown",
        "user_cooldown",
        "queue_full",
        "expired",
    ]
    decided_at_ms: int
    started_at_ms: int | None = None
    finished_at_ms: int | None = None
    steps: tuple[SimulationStep, ...] = ()


class SimulationReport(BaseModel):
    model_config = ConfigDict(frozen=True)
    config_revision: int
    profile_id: str
    profile_name: str
    platform: Platform
    decisions: tuple[SimulationDecision, ...]
    planned_count: int
    rejected_count: int
    duration_ms: int
    limits: ControlLimits


def simulate(
    snapshot: ConfigSnapshot,
    messages: tuple[SimulationMessage, ...],
    *,
    profile_id: str | None = None,
    platform: Platform | None = None,
) -> SimulationReport:
    scenario = SimulationScenario(messages=messages)
    profile_id = profile_id or snapshot.config.active_profile_id
    if not any(p.id == profile_id for p in snapshot.config.profiles):
        raise AppError("profile_not_found", "Nie znaleziono profilu.", status=404)
    # Select the saved profile/platform, never mutate the live snapshot.
    config = snapshot.config.model_copy(
        update={
            "active_profile_id": profile_id,
            "platform": platform or snapshot.config.platform,
        }
    )
    now = 0
    matcher = Matcher(config)
    limits = config.active_profile.limits
    limiter = RateLimiter(limits)
    decisions = []
    pending = deque()
    busy_until = None

    def plan(record, definition: ActionDefinition, start):
        cursor = start
        steps = []
        for step in definition.steps:
            duration = getattr(step, "duration_ms", 0)
            steps.append(
                SimulationStep(
                    type=step.type,
                    keys=getattr(step, "keys", ()),
                    start_ms=cursor,
                    end_ms=cursor + duration,
                    duration_ms=duration,
                )
            )
            cursor += duration
        record.update(
            reason="planned",
            decided_at_ms=start,
            started_at_ms=start,
            finished_at_ms=cursor,
            steps=tuple(steps),
        )
        return cursor

    def advance(until):
        nonlocal busy_until
        if busy_until is not None and busy_until > until:
            return
        cursor = busy_until if busy_until is not None else until
        while pending:
            record, definition = pending.popleft()
            if action_expired(cursor, record["offset_ms"] + limits.action_ttl_ms):
                record.update(reason="expired", decided_at_ms=cursor)
                continue
            busy_until = plan(record, definition, cursor)
            if busy_until > until:
                return
            cursor = busy_until
        busy_until = None

    for original_index, message in sorted(
        enumerate(scenario.messages), key=lambda pair: pair[1].offset_ms
    ):
        now = message.offset_ms
        advance(now)
        decision = matcher.resolve(message.user_id, message.comment)
        record = {
            "message_index": original_index,
            "offset_ms": now,
            "user_id": message.user_id,
            "actor_id": decision.actor_id,
            "comment": message.comment,
            "trigger": decision.trigger,
            "mapping_id": decision.mapping_id,
            "reason": decision.reason,
            "decided_at_ms": now,
        }
        decisions.append(record)
        if decision.reason != "matched":
            continue
        limit = limiter.check(decision.actor_id, decision.mapping_id, now / 1000)
        if limit.reason:
            record["reason"] = limit.reason
            continue
        definition = decision.mapping.action
        if busy_until is None:
            busy_until = plan(record, definition, now)
        elif queue_has_capacity(len(pending), limits.queue_capacity):
            pending.append((record, definition))
        else:
            record["reason"] = "queue_full"
            continue
        limiter.commit(decision.actor_id, decision.mapping_id, now / 1000)
    # Finish virtual output, including a hold extending past the last input message.
    while busy_until is not None:
        advance(busy_until)
    results = tuple(SimulationDecision(**d) for d in decisions)
    planned = sum(d.reason == "planned" for d in results)
    return SimulationReport(
        limits=limits,
        config_revision=snapshot.revision,
        profile_id=profile_id,
        profile_name=config.active_profile.name,
        platform=config.platform,
        decisions=results,
        planned_count=planned,
        rejected_count=len(results) - planned,
        duration_ms=max(max(d.decided_at_ms, d.finished_at_ms or 0) for d in results),
    )

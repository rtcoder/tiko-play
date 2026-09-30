"""Current output limits shared by the live executor and the virtual simulator."""

ACTION_COOLDOWN_SECONDS = 0.3
ACTION_TTL_SECONDS = 1.0
QUEUE_CAPACITY = 100


def queue_has_capacity(pending_count: int) -> bool:
    return pending_count < QUEUE_CAPACITY


def action_expired(now: float, expires_at: float) -> bool:
    # Preserve the live executor's existing boundary (equality is still valid).
    return now > expires_at

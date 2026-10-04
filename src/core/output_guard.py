"""Process identity and fail-closed output checks. No window titles or public output."""

import threading

from pydantic import BaseModel, ConfigDict, Field


class TargetIdentity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    app: str = Field(min_length=1, max_length=4096)
    pid: int = Field(gt=0)
    started: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=256)

    def same_process(self, other):
        return other is not None and (self.app, self.pid, self.started) == (
            other.app,
            other.pid,
            other.started,
        )


class OutputGuard:
    def __init__(self, port):
        self.port = port
        self._lock = threading.RLock()
        self.enabled = False
        self.target = None

    def configure(self, enabled, target):
        with self._lock:
            self.enabled = enabled
            self.target = target

    def can_execute(self):
        with self._lock:
            if not self.enabled:
                return True
            target = self.target
        try:
            return bool(target and target.same_process(self.port.current_target()))
        except Exception:  # Fail closed on permission or native API failures.
            return False

    def targets(self):
        return self.port.targets()

    def state(self):
        with self._lock:
            return {
                "enabled": self.enabled,
                "target": self.target.model_dump() if self.target else None,
            }

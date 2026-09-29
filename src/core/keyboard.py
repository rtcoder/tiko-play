import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass, replace

from src.core.actions import ActionDefinition, HoldStep, PressStep, WaitStep
from src.core.models import AppError


@dataclass(frozen=True)
class KeyAction:
    keys: tuple[str, ...]
    generation: int
    created_at: float
    definition: ActionDefinition | None = None
    mapping_id: str = ""
    actor_id: str = ""
    output_epoch: int | None = None
    expires_at: float | None = None

    def __post_init__(self):
        if self.definition is None:
            object.__setattr__(
                self, "definition", ActionDefinition(steps=(PressStep(keys=self.keys),))
            )
        if self.expires_at is None:
            object.__setattr__(self, "expires_at", self.created_at + 1)


class ReleaseError(Exception):
    pass


class KeyboardExecutor:
    def __init__(self, port, clock=time.monotonic, report=lambda *a: None):
        self.port = port
        self.clock = clock
        self.report = report
        self._pending = deque()
        self._condition = threading.Condition()
        self._generation = None
        self._epoch = 0
        self._closed = False
        self._fault = False
        self._last_drop = float("-inf")
        self._thread = threading.Thread(
            target=self._run, name="TikoPlay-keyboard", daemon=True
        )
        self._thread.start()

    @property
    def output_epoch(self):
        with self._condition:
            return self._epoch

    def enable(self, generation):
        with self._condition:
            if self._fault or self._closed:
                raise AppError(
                    "keyboard_release_error",
                    "Nie udało się zwolnić klawiszy. Wyjście zablokowane. Sprawdź klawisze i uruchom aplikację ponownie.",
                )
            self._pending.clear()
            self._epoch += 1
            self._generation = generation
            self._condition.notify_all()

    def disable(self):
        with self._condition:
            self._epoch += 1
            self._generation = None
            self._pending.clear()
            self._condition.notify_all()

    def _drop(self):
        now = self.clock()
        if now - self._last_drop >= 1:
            self._last_drop = now
            self.report("dropped", {})

    def submit(self, action):
        with self._condition:
            if self._closed or self._fault or self._generation != action.generation:
                return False
            if action.output_epoch is not None and action.output_epoch != self._epoch:
                return False
            if len(self._pending) >= 100:
                self._drop()
                return False
            self._pending.append(replace(action, output_epoch=self._epoch))
            self._condition.notify()
            return True

    def _valid(self, action):
        return (
            not self._closed
            and not self._fault
            and self._generation == action.generation
            and self._epoch == action.output_epoch
        )

    def _cancelled(self, action):
        with self._condition:
            return not self._valid(action)

    def _wait(self, action, duration_ms):
        # Use real monotonic time for waiting; the injected queue clock may be frozen.
        deadline = time.monotonic() + duration_ms / 1000
        while True:
            if self._cancelled(action):
                return True
            check = getattr(self.port, "check_failsafe", None)
            if check is not None:
                check()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            with self._condition:
                if self._condition.wait_for(
                    lambda: not self._valid(action), timeout=min(remaining, 0.05)
                ):
                    return True

    def _release(self, held):
        failed = False
        # Attempt all releases even when one OS call fails. Never claim success then.
        for key in reversed(held):
            try:
                self.port.key_up(key)
            except Exception:  # noqa: BLE001 - every failed release must fence output
                failed = True
        if failed:
            raise ReleaseError()

    def _execute(self, action):
        for step in action.definition.steps:
            if self._cancelled(action):
                return False
            if isinstance(step, WaitStep):
                if self._wait(action, step.duration_ms):
                    return False
                continue
            held = []
            try:
                for key in dict.fromkeys(step.keys):
                    if self._cancelled(action):
                        return False
                    # Record before calling: a driver can send input and then raise.
                    held.append(key)
                    self.port.key_down(key)
                if isinstance(step, HoldStep) and self._wait(action, step.duration_ms):
                    return False
            finally:
                self._release(held)
        return not self._cancelled(action)

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or self._pending)
                if self._closed:
                    return
                action = self._pending.popleft()
                if not self._valid(action):
                    continue
                if self.clock() > action.expires_at:
                    self._drop()
                    continue
            try:
                if self._execute(action):
                    self.report(
                        "executed",
                        {
                            "keys": list(action.keys),
                            "action": action.definition.model_dump(mode="json"),
                            "mapping_id": action.mapping_id,
                            "generation": action.generation,
                        },
                    )
            except Exception as exc:  # noqa: BLE001 - isolate OS/driver failures
                release_failed = isinstance(exc, ReleaseError)
                with self._condition:
                    if release_failed:
                        self._fault = True
                    if release_failed or self._valid(action):
                        self._generation = None
                        self._pending.clear()
                        self._epoch += 1
                    self._condition.notify_all()
                code = (
                    "keyboard_release_error"
                    if release_failed
                    else (
                        "keyboard_failsafe"
                        if type(exc).__name__ == "FailSafeException"
                        else "keyboard_error"
                    )
                )
                self.report(
                    "error",
                    {
                        "generation": action.generation,
                        "code": code,
                        "message": "Nie udało się zwolnić klawiszy. Wyjście zablokowane. Sprawdź klawisze i uruchom aplikację ponownie."
                        if release_failed
                        else "Wysyłanie klawiszy zatrzymane. Sprawdź uprawnienia lub fail-safe PyAutoGUI.",
                    },
                )

    async def close(self, timeout=2):
        with self._condition:
            self._closed = True
            self._generation = None
            self._pending.clear()
            self._condition.notify_all()
        await asyncio.to_thread(self._thread.join, timeout)

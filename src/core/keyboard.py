import asyncio
import threading
import time
from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class KeyAction:
    keys: tuple[str, ...]
    generation: int
    created_at: float


class KeyboardExecutor:
    def __init__(self, port, clock=time.monotonic, report=lambda *a: None):
        self.port = port
        self.clock = clock
        self.report = report
        self._pending = deque()
        self._condition = threading.Condition()
        self._generation = None
        self._closed = False
        self._last_drop = float("-inf")
        self._thread = threading.Thread(
            target=self._run, name="TikoPlay-keyboard", daemon=True
        )
        self._thread.start()

    def enable(self, generation):
        with self._condition:
            self._pending.clear()
            self._generation = generation

    def disable(self):
        with self._condition:
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
            if self._closed or self._generation != action.generation:
                return False
            if len(self._pending) >= 100:
                self._drop()
                return False
            self._pending.append(action)
            self._condition.notify()
            return True

    def _run(self):
        while True:
            with self._condition:
                self._condition.wait_for(lambda: self._closed or self._pending)
                if self._closed:
                    return
                action = self._pending.popleft()
                if action.generation != self._generation:
                    continue
                if self.clock() - action.created_at > 1:
                    self._drop()
                    continue
                # Claim is the start boundary. disable() fences everything not yet claimed.
            try:
                self.port.execute(action.keys)
                self.report(
                    "executed",
                    {"keys": list(action.keys), "generation": action.generation},
                )
            except Exception as exc:
                with self._condition:
                    if self._generation == action.generation:
                        self._generation = None
                        self._pending.clear()
                code = (
                    "keyboard_failsafe"
                    if type(exc).__name__ == "FailSafeException"
                    else "keyboard_error"
                )
                self.report(
                    "error",
                    {
                        "generation": action.generation,
                        "code": code,
                        "message": "Wysyłanie klawiszy zatrzymane. Sprawdź uprawnienia lub fail-safe PyAutoGUI.",
                    },
                )

    async def close(self, timeout=2):
        with self._condition:
            self._closed = True
            self._generation = None
            self._pending.clear()
            self._condition.notify_all()
        await asyncio.to_thread(self._thread.join, timeout)

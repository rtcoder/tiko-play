import asyncio
import time
from contextlib import suppress
from src.core.models import ListenerState, AppError
from src.core.matching import Matcher
from src.core.keyboard import KeyAction


class ListenerService:
    def __init__(
        self, factory, keyboard, events, clock=time.monotonic, sleep=asyncio.sleep
    ):
        self.factory = factory
        self.keyboard = keyboard
        self.events = events
        self.clock = clock
        self.sleep = sleep
        self._state = ListenerState()
        self._task = None
        self._client = None
        self._stop = False
        self._cancel_requested = False
        self._cleaning = False

    def state(self):
        return self._state.model_copy(deep=True)

    def _change(self, **kwargs):
        self._state = self._state.model_copy(update=kwargs)
        self.events.publish("status", self._state.model_dump())

    def start(self, snapshot):
        if self._state.status in ("connecting", "connected"):
            return self.state()
        if self._state.status == "stopping" or (self._task and not self._task.done()):
            raise AppError(
                "listener_busy", "Poczekaj na zatrzymanie nasłuchu", status=409
            )
        if not snapshot.config.active_source().channel:
            raise AppError("streamer_required", "Podaj nick streamera", status=422)
        self._stop = False
        self._cancel_requested = False
        self._cleaning = False
        self._change(
            status="connecting",
            output="disabled",
            error=None,
            generation=self._state.generation + 1,
            active_config_revision=snapshot.revision,
            active_platform=snapshot.config.platform,
            active_channel=snapshot.config.active_source().channel,
        )
        self._task = asyncio.create_task(self._run(snapshot))
        return self.state()

    def authorization_lost(self):
        if self._state.active_platform != "twitch" or self._state.status not in ("connecting", "connected"):
            return
        self.keyboard.disable()
        self._change(status="error", output="disabled", error={
            "code": "twitch_auth_required", "message": "Sesja Twitcha nie jest dostępna. Połącz konto ponownie."})
        if self._task and not self._task.done():
            self._cancel_once()

    def request_stop(self):
        self._stop = True
        self.keyboard.disable()
        if self._task and not self._task.done():
            self._change(status="stopping", output="disabled")
            self._cancel_once()
        else:
            self._change(status="stopped", output="disabled", error=None)
        return self.state()

    def _cancel_once(self):
        if not self._cancel_requested and not self._cleaning:
            self._cancel_requested = True
            self._task.cancel()

    async def stop(self):
        self.request_stop()
        if self._task:
            with suppress(asyncio.CancelledError):
                await asyncio.shield(self._task)
        self._change(status="stopped", output="disabled", error=None)
        return self.state()

    def keyboard_result(self, kind, payload):
        if payload.get("generation", self._state.generation) != self._state.generation:
            return
        self.events.publish("action" if kind == "executed" else kind, payload)
        if kind == "error":
            self.keyboard.disable()
            self._change(status="error", output="disabled", error=payload)
            if self._task and not self._task.done():
                self._cancel_once()

    async def _run(self, snapshot):
        child = None
        countdown = None
        try:
            matcher = Matcher(snapshot.config, self.clock)
            generation = self._state.generation

            async def comment(user, text):
                if generation != self._state.generation or self._stop or self._state.status not in ("connecting", "connected"):
                    return
                self.events.publish("comment", {"user": user, "comment": text,
                    "platform": snapshot.config.platform, "channel": snapshot.config.active_source().channel,
                    "generation": generation})
                if self._stop or self._state.output != "enabled":
                    return
                keys = matcher.match(user, text)
                if keys:
                    self.keyboard.submit(KeyAction(keys, generation, self.clock()))

            self._client = self.factory(snapshot.config)
            child = await self._client.connect(comment)
            self._change(
                status="connected",
                output="countdown" if snapshot.config.countdown_enabled else "disabled",
            )
            if snapshot.config.countdown_enabled:
                countdown = asyncio.create_task(self.sleep(3))
                done, _ = await asyncio.wait(
                    [child, countdown], return_when=asyncio.FIRST_COMPLETED
                )
                if child in done:
                    await child
                    raise AppError(
                        "connection_lost", "Połączenie z czatem zostało zakończone"
                    )
            if self._stop:
                return
            self.keyboard.enable(generation)
            self._change(output="enabled")
            await child
            raise AppError(
                "connection_lost", "Połączenie z czatem zostało zakończone"
            )
        except asyncio.CancelledError:
            self.keyboard.disable()
            if not self._stop and self._state.status != "error":
                self._change(
                    status="error",
                    output="disabled",
                    error={
                        "code": "connection_lost",
                        "message": "Połączenie z czatem zostało przerwane",
                    },
                )
        except Exception as exc:
            self.keyboard.disable()
            error = (
                exc
                if isinstance(exc, AppError)
                else AppError(
                    "connection_error",
                    "Nie udało się połączyć z czatem. Sprawdź kanał i sieć.",
                )
            )
            self._change(status="error", output="disabled", error=error.as_dict())
        finally:
            self._cleaning = True
            self.keyboard.disable()
            for task in (countdown, child):
                if task:
                    task.cancel()
                    with suppress(asyncio.CancelledError, Exception):
                        await task
            if self._client:
                with suppress(Exception, asyncio.CancelledError):
                    await asyncio.wait_for(self._client.disconnect(), 2)
            self._client = None
            if self._stop:
                self._change(status="stopped", output="disabled")

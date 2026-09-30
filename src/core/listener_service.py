import asyncio
import time
from copy import deepcopy
from contextlib import suppress

from src.core.keyboard import KeyAction
from src.core.matching import Matcher
from src.core.models import AppError, ListenerState


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
        self.active_snapshot = None
        self.last_executed = None
        self._execution_id = 0
        self._task = None
        self._client = None
        self._stop = False
        self._cancel_requested = False
        self._cleaning = False
        self._stop_revision = 0

    def state(self):
        return self._state.model_copy(deep=True)

    def _change(self, **kwargs):
        self._state = self._state.model_copy(update=kwargs)
        self.events.publish("status", self._state.model_dump())

    @property
    def stop_revision(self):
        return self._stop_revision

    def start(self, snapshot, *, expected_stop_revision=None):
        if (
            expected_stop_revision is not None
            and expected_stop_revision != self._stop_revision
        ):
            raise AppError(
                "start_cancelled",
                "Uruchomienie nasłuchu anulowano przez Stop.",
                status=409,
            )
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
        self.active_snapshot = snapshot
        self.last_executed = None
        self._change(
            status="connecting",
            output="disabled",
            error=None,
            generation=self._state.generation + 1,
            active_config_revision=snapshot.revision,
            active_platform=snapshot.config.platform,
            active_channel=snapshot.config.active_source().channel,
            active_profile_id=snapshot.config.active_profile.id,
            active_profile_name=snapshot.config.active_profile.name,
        )
        self._task = asyncio.create_task(self._run(snapshot))
        return self.state()

    def authorization_lost(self):
        if self._state.active_platform != "twitch" or self._state.status not in (
            "connecting",
            "connected",
        ):
            return
        self.keyboard.disable()
        self._change(
            status="error",
            output="disabled",
            error={
                "code": "twitch_auth_required",
                "message": "Sesja Twitcha nie jest dostępna. Połącz konto ponownie.",
            },
        )
        if self._task and not self._task.done():
            self._cancel_once()

    def request_stop(self):
        self._stop_revision += 1
        self._stop = True
        self.keyboard.disable()
        if self._task and not self._task.done():
            self._change(status="stopping", output="disabled")
            self._cancel_once()
        else:
            self._change(status="stopped", output="disabled")
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
        self._change(status="stopped", output="disabled")
        return self.state()

    def keyboard_result(self, kind, payload):
        if (
            payload.get("code") != "keyboard_release_error"
            and payload.get("generation", self._state.generation)
            != self._state.generation
        ):
            return
        if kind == "executed":
            self._execution_id += 1
            self.last_executed = {**deepcopy(payload), "id": self._execution_id}
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
                if (
                    generation != self._state.generation
                    or self._stop
                    or self._state.status not in ("connecting", "connected")
                ):
                    return
                self.events.publish(
                    "comment",
                    {
                        "user": user,
                        "comment": text,
                        "platform": snapshot.config.platform,
                        "channel": snapshot.config.active_source().channel,
                        "generation": generation,
                    },
                )
                if self._stop or self._state.output != "enabled":
                    return
                mapping = matcher.match_mapping(user, text)
                if mapping:
                    self.keyboard.submit(
                        KeyAction(
                            (),
                            generation,
                            self.clock(),
                            definition=mapping.action,
                            mapping_id=mapping.id,
                            actor_id=user[:128],
                            comment=text[:2000],
                        )
                    )

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
            raise AppError("connection_lost", "Połączenie z czatem zostało zakończone")
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

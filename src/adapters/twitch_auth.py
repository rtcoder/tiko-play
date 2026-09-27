"""Device authorization with serialized credential rotation and logout fences."""

import asyncio
import time
from contextlib import suppress
from dataclasses import replace
from urllib.parse import urlsplit

import httpx

from src.adapters.twitch_credentials import TwitchCredentials
from src.core.models import AppError

OAUTH = "https://id.twitch.tv/oauth2"
SCOPE = "user:read:chat"


def auth_error(code="twitch_auth_required", message="Połącz ponownie konto Twitch."):
    return AppError(code, message, status=409)


def activation_url(value):
    u = urlsplit(value)
    if (
        u.scheme != "https"
        or u.hostname not in ("www.twitch.tv", "twitch.tv")
        or u.username
        or u.password
        or u.port not in (None, 443)
    ):
        raise auth_error(
            "twitch_protocol_error", "Niepoprawny adres aktywacji Twitcha."
        )
    return value


class TwitchAuthService:
    def __init__(
        self, client_id, store, http, events, *, clock=time.time, sleep=asyncio.sleep
    ):
        self.client_id, self.store, self.http, self.events = (
            client_id,
            store,
            http,
            events,
        )
        self.clock, self.sleep = clock, sleep
        self._credentials = None
        self._validated_at = float("-inf")
        self._status, self._error = "disconnected", None
        self._epoch = 0
        self._attempt = 0
        self._lock = asyncio.Lock()
        self._poll = None
        self._monitor = None
        self._callbacks = set()
        self._closed = False

    def state(self):
        return dict(
            configured=bool(self.client_id),
            status=self._status,
            attempt_id=self._attempt,
            login=self._credentials.login if self._credentials else None,
            error=self._error,
        )

    def _publish(self, status, error=None):
        self._status, self._error = status, error.as_dict() if error else None
        self.events.publish("twitch_auth", self.state())

    def subscribe_invalidated(self, callback):
        self._callbacks.add(callback)
        return lambda: self._callbacks.discard(callback)

    def _notify(self):
        for callback in tuple(self._callbacks):
            callback()

    async def _save(self, value):
        task = asyncio.create_task(self.store.save(value))
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            await task
            raise

    async def _invalidate_locked(self, error):
        self._credentials = None
        self._notify()
        self._publish("error", error)
        try:
            await self.store.delete()
        except AppError as exc:
            self._publish("error", exc)

    async def _validate(self, credentials):
        response = await self.http.get(
            OAUTH + "/validate",
            headers={"Authorization": "OAuth " + credentials.access_token},
            timeout=10,
        )
        if response.status_code == 401:
            raise auth_error()
        if response.status_code != 200:
            raise auth_error(
                "twitch_network_error",
                "Nie można zweryfikować sesji Twitcha. Sprawdź sieć.",
            )
        data = response.json()
        if (
            data.get("client_id") != self.client_id
            or (credentials.user_id and data.get("user_id") != credentials.user_id)
            or SCOPE not in data.get("scopes", [])
            or not data.get("user_id")
            or not data.get("login")
        ):
            raise auth_error()
        return replace(
            credentials,
            user_id=data["user_id"],
            login=data["login"],
            expires_at=self.clock() + float(data["expires_in"]),
        )

    async def _ensure_locked(self, epoch):
        value = self._credentials
        if value is None or value.client_id != self.client_id:
            raise auth_error()
        refreshing = value.expires_at <= self.clock() + 60
        try:
            if refreshing:
                response = await self.http.post(
                    OAUTH + "/token",
                    data={
                        "client_id": self.client_id,
                        "grant_type": "refresh_token",
                        "refresh_token": value.refresh_token,
                    },
                    timeout=10,
                )
                if response.status_code != 200:
                    raise auth_error()
                data = response.json()
                value = replace(
                    value,
                    access_token=data["access_token"],
                    refresh_token=data["refresh_token"],
                    expires_at=self.clock() + float(data["expires_in"]),
                )
            if refreshing or self.clock() - self._validated_at >= 3600:
                value = await self._validate(value)
                if epoch != self._epoch or self._closed:
                    raise auth_error()
                await self._save(value)
                if epoch != self._epoch or self._closed:
                    raise auth_error()
                self._credentials, self._validated_at = value, self.clock()
            return value
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            error = (
                auth_error()
                if refreshing
                else auth_error(
                    "twitch_network_error",
                    "Nie można zweryfikować sesji Twitcha. Sprawdź sieć.",
                )
            )
            if epoch == self._epoch:
                if refreshing:
                    await self._invalidate_locked(error)
                else:
                    self._notify()
                    self._publish("error", error)
            raise error from None
        except AppError as exc:
            if epoch == self._epoch:
                if exc.code == "twitch_network_error":
                    self._notify()
                    self._publish("error", exc)
                else:
                    await self._invalidate_locked(exc)
            raise

    def _start_monitor(self):
        if self._monitor is None or self._monitor.done():
            self._monitor = asyncio.create_task(self._watch())

    async def _watch(self):
        while not self._closed:
            # A separate real timer avoids tight loops with injected DCF sleeps.
            await asyncio.sleep(60)
            if self._credentials:
                with suppress(AppError):
                    await self.credentials()

    async def restore(self):
        if not self.client_id:
            return
        epoch = self._epoch
        async with self._lock:
            try:
                value = await self.store.load()
                if epoch != self._epoch or self._closed:
                    return
                self._credentials = value
                if value:
                    await self._ensure_locked(epoch)
                    if epoch == self._epoch:
                        self._publish("connected")
            except AppError as exc:
                if epoch == self._epoch:
                    self._credentials = None
                    self._publish("error", exc)
        self._start_monitor()

    async def credentials(self):
        epoch = self._epoch
        async with self._lock:
            if epoch != self._epoch or self._closed:
                raise auth_error()
            value = await self._ensure_locked(epoch)
            if self._status == "error":
                self._publish("connected")
            return value

    async def cancel(self):
        self._attempt += 1
        task, self._poll = self._poll, None
        if task and task is not asyncio.current_task():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        if not self._closed:
            self._publish("connected" if self._credentials else "disconnected")

    async def start(self):
        if not self.client_id or self._closed:
            raise auth_error(
                "twitch_not_configured",
                "Brak identyfikatora aplikacji Twitch. Ustaw TIKOPLAY_TWITCH_CLIENT_ID.",
            )
        await self.cancel()
        attempt, epoch = self._attempt, self._epoch
        try:
            response = await self.http.post(
                OAUTH + "/device",
                data={"client_id": self.client_id, "scopes": SCOPE},
                timeout=10,
            )
            if response.status_code != 200:
                raise auth_error(
                    "twitch_login_error", "Nie można rozpocząć logowania Twitcha."
                )
            data = response.json()
            result = dict(
                user_code=str(data["user_code"]),
                verification_uri=activation_url(data["verification_uri"]),
                expires_at=self.clock() + float(data["expires_in"]),
            )
            interval = max(1, float(data["interval"]))
            device_code = data["device_code"]
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise auth_error(
                "twitch_login_error",
                "Nie można rozpocząć logowania Twitcha. Sprawdź sieć.",
            ) from None
        if attempt != self._attempt or epoch != self._epoch or self._closed:
            raise auth_error("twitch_login_cancelled", "Logowanie anulowano.")
        self._publish("pending")
        self._poll = asyncio.create_task(
            self._poll_device(
                attempt, epoch, device_code, interval, result["expires_at"]
            )
        )
        return {**self.state(), **result}

    async def _poll_device(self, attempt, epoch, device_code, interval, deadline):
        try:
            while self.clock() < deadline:
                await self.sleep(interval)
                if self.clock() >= deadline:
                    break
                response = await self.http.post(
                    OAUTH + "/token",
                    data={
                        "client_id": self.client_id,
                        "scopes": SCOPE,
                        "device_code": device_code,
                        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    },
                    timeout=10,
                )
                if attempt != self._attempt or epoch != self._epoch or self._closed:
                    return
                data = response.json()
                if response.status_code != 200:
                    message = data.get("message", data.get("error"))
                    if message == "authorization_pending":
                        continue
                    if message == "slow_down" or response.status_code == 429:
                        interval += 5
                        continue
                    raise auth_error(
                        "twitch_login_error",
                        "Logowanie odrzucone lub kod wygasł. Spróbuj ponownie.",
                    )
                value = TwitchCredentials(
                    self.client_id,
                    "",
                    "",
                    data["access_token"],
                    data["refresh_token"],
                    self.clock() + float(data["expires_in"]),
                )
                value = await self._validate(value)
                async with self._lock:
                    if attempt != self._attempt or epoch != self._epoch or self._closed:
                        return
                    try:
                        await self._save(value)
                        if (
                            attempt != self._attempt
                            or epoch != self._epoch
                            or self._closed
                        ):
                            raise asyncio.CancelledError()
                    except asyncio.CancelledError:
                        if self._credentials:
                            await self._save(self._credentials)
                        else:
                            await self.store.delete()
                        raise
                    if self._credentials:
                        self._notify()  # A running chat must not silently change accounts.
                    self._credentials, self._validated_at = value, self.clock()
                    self._publish("connected")
                    self._start_monitor()
                return
            raise auth_error(
                "twitch_login_expired",
                "Kod Twitcha wygasł. Rozpocznij logowanie ponownie.",
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            error = (
                exc
                if isinstance(exc, AppError)
                else auth_error(
                    "twitch_login_error", "Nie udało się połączyć konta Twitch."
                )
            )
            if attempt == self._attempt and epoch == self._epoch and not self._closed:
                self._publish("error", error)

    async def disconnect(self):
        self._epoch += 1
        old = self._credentials
        self._credentials = None
        self._notify()
        await self.cancel()
        async with self._lock:
            await self.store.delete()
        self._publish("disconnected")
        if old:
            with suppress(Exception):
                await self.http.post(
                    OAUTH + "/revoke",
                    data={"client_id": self.client_id, "token": old.access_token},
                    timeout=5,
                )

    async def close(self):
        self._closed = True
        self._epoch += 1
        await self.cancel()
        if self._monitor:
            self._monitor.cancel()
            await asyncio.gather(self._monitor, return_exceptions=True)

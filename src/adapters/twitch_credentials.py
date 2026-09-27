"""One credential record, stored only in the operating system's vault."""
import asyncio
import json
import sys
from dataclasses import asdict, dataclass, field
from typing import Protocol
from src.core.models import AppError


@dataclass(frozen=True)
class TwitchCredentials:
    client_id: str
    user_id: str
    login: str
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    expires_at: float


class CredentialStore(Protocol):
    async def load(self) -> TwitchCredentials | None: ...
    async def save(self, credentials: TwitchCredentials) -> None: ...
    async def delete(self) -> None: ...


class NativeCredentialStore:
    SERVICE = "TikoPlay.Twitch"
    ACCOUNT = "oauth"

    def __init__(self, *, backend=None):
        self._backend = backend

    def native_backend(self):
        if self._backend is not None:
            return self._backend
        if sys.platform == "darwin":
            from keyring.backends.macOS import Keyring
        elif sys.platform == "win32":
            from keyring.backends.Windows import WinVaultKeyring as Keyring
        else:
            raise AppError("credential_store_unavailable", "Brak obsługi systemowego magazynu poświadczeń Twitcha.")
        self._backend = Keyring()
        return self._backend

    async def _io(self, operation):
        try:
            # Keep callers' locks held until a non-cancellable native write finishes.
            task = asyncio.create_task(asyncio.to_thread(operation))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise
        except Exception:
            raise AppError("credential_store_unavailable", "Nie można odczytać lub zapisać konta w systemowym magazynie poświadczeń.") from None

    async def load(self):
        def read():
            raw = self.native_backend().get_password(self.SERVICE, self.ACCOUNT)
            if raw is None:
                return None
            data = json.loads(raw)
            result = TwitchCredentials(**data)
            if not all(isinstance(data[k], str) and data[k] for k in ("client_id", "user_id", "login", "access_token", "refresh_token")) or not isinstance(result.expires_at, (int, float)):
                raise ValueError("Invalid credential record")
            return result
        return await self._io(read)

    async def save(self, credentials):
        await self._io(lambda: self.native_backend().set_password(self.SERVICE, self.ACCOUNT, json.dumps(asdict(credentials))))

    async def delete(self):
        def remove():
            backend = self.native_backend()
            if backend.get_password(self.SERVICE, self.ACCOUNT) is not None:
                backend.delete_password(self.SERVICE, self.ACCOUNT)
        await self._io(remove)

import asyncio
import threading
import pytest
from src.core.models import AppError


async def test_credential_store_roundtrip_off_loop_and_redacted_errors():
    from src.adapters.twitch_credentials import NativeCredentialStore, TwitchCredentials
    threads=[]
    class Backend:
        value=None
        def get_password(self,*args): threads.append(threading.get_ident()); return self.value
        def set_password(self,*args): threads.append(threading.get_ident()); self.value=args[-1]
        def delete_password(self,*args): self.value=None
    backend=Backend()
    # Constructor injection is an IO seam; production always selects a native backend.
    store=NativeCredentialStore(backend=backend)
    value=TwitchCredentials('c','u','alice','SECRET_A','SECRET_R',1234)
    await store.save(value)
    assert await store.load()==value
    assert threading.get_ident() not in threads
    assert 'SECRET' not in repr(value)
    await store.delete(); assert await store.load() is None
    backend.value='broken SECRET'
    with pytest.raises(AppError) as exc: await store.load()
    assert 'SECRET' not in str(exc.value)


def test_unsupported_platform_never_falls_back_to_plaintext(monkeypatch):
    from src.adapters.twitch_credentials import NativeCredentialStore
    monkeypatch.setattr('src.adapters.twitch_credentials.sys.platform','linux')
    with pytest.raises(AppError): NativeCredentialStore().native_backend()

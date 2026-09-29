import sys
from types import SimpleNamespace

import pytest

from src.adapters.pyautogui_keyboard import PyAutoGUIKeyboard
from src.adapters.tiktok import TikTokAdapter
from src.core.models import AppError


def test_pyautogui_adapter_preserves_combo(monkeypatch):
    calls = []
    monkeypatch.setitem(
        sys.modules,
        "pyautogui",
        SimpleNamespace(
            press=lambda k: calls.append(("press", k)),
            hotkey=lambda *k: calls.append(("hotkey", *k)),
        ),
    )
    port = PyAutoGUIKeyboard()
    port.execute(("left",))
    port.execute(("ctrl", "shift", "a"))
    assert calls == [("press", "left"), ("hotkey", "ctrl", "shift", "a")]


@pytest.mark.parametrize(
    "name,code",
    [
        ("UserOfflineError", "streamer_offline"),
        ("UserNotFoundError", "streamer_not_found"),
        ("AlreadyConnectedError", "already_connected"),
        ("RuntimeError", "connection_error"),
    ],
)
async def test_tiktok_errors_are_user_facing(monkeypatch, name, code):
    class Fake:
        def __init__(self, **kwargs):
            pass

        def on(self, event):
            return lambda fn: fn

        async def start(self):
            raise type(name, (Exception,), {})("provider details")

        async def disconnect(self):
            pass

        async def close(self):
            pass

    monkeypatch.setitem(
        sys.modules, "TikTokLive", SimpleNamespace(TikTokLiveClient=Fake)
    )
    monkeypatch.setitem(
        sys.modules, "TikTokLive.events", SimpleNamespace(CommentEvent=object)
    )
    adapter = TikTokAdapter("a")
    with pytest.raises(AppError) as e:
        await adapter.connect(lambda *a: None)
    assert e.value.code == code and "provider details" not in e.value.message
    await adapter.disconnect()


@pytest.mark.parametrize("cancelled", [False, True])
async def test_tiktok_disconnect_always_closes_http_sessions(cancelled):
    import asyncio

    closed = []

    class Client:
        async def disconnect(self):
            if cancelled:
                raise asyncio.CancelledError()

        async def close(self):
            closed.append(True)

    adapter = TikTokAdapter("a")
    adapter.client = Client()
    try:
        await adapter.disconnect()
    except asyncio.CancelledError:
        pass
    assert closed == [True]


def test_cleanup_releases_even_when_pyautogui_failsafe_is_active(monkeypatch):
    import functools
    import sys
    from types import SimpleNamespace

    from src.adapters.pyautogui_keyboard import PyAutoGUIKeyboard

    calls = []

    class FailSafeException(Exception):
        pass

    def raw_up(key, **kwargs):
        calls.append(("up", key))

    @functools.wraps(raw_up)
    def guarded_up(key, **kwargs):
        raise FailSafeException()

    def guarded_down(key, **kwargs):
        raise FailSafeException()

    monkeypatch.setitem(
        sys.modules,
        "pyautogui",
        SimpleNamespace(keyUp=guarded_up, keyDown=guarded_down),
    )
    port = PyAutoGUIKeyboard()
    port.key_up("ctrl")
    assert calls == [("up", "ctrl")]
    with pytest.raises(FailSafeException):
        port.key_down("a")

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

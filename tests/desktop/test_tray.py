import sys
from types import SimpleNamespace
from unittest.mock import Mock

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QSystemTrayIcon
import pytest

from src.desktop import tray as module


class Host(QObject):
    state_changed = Signal(dict)
    request_stop = Mock()


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_repeated_tray_clicks_preserve_process_and_menu_actions(qapp, monkeypatch, tmp_path, platform):
    monkeypatch.setattr(sys, "platform", platform)
    monkeypatch.setattr(QSystemTrayIcon, "isSystemTrayAvailable", lambda *args: True)
    monkeypatch.setattr(QSystemTrayIcon, "show", lambda self: None)
    controller = SimpleNamespace(open_panel=Mock(), quit=Mock())
    host = Host()
    tray = module.TrayController(host, controller, tmp_path)
    try:
        if platform == "darwin":
            # Native attached-menu tracking crashes inside Qt on macOS 27.
            assert tray.tray.contextMenu() is None
        else:
            assert tray.tray.contextMenu() is tray.menu
        popup = Mock()
        monkeypatch.setattr(tray.menu, "popup", popup)
        for _ in range(20):
            tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Trigger)
        assert controller.open_panel.call_count == 20
        controller.quit.assert_not_called()
        tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Context)
        assert controller.open_panel.call_count == 20
        assert popup.call_count == (1 if platform == "darwin" else 0)
        next(a for a in tray.menu.actions() if a.text() == "Zakończ TikoPlay").trigger()
        controller.quit.assert_called_once()
    finally:
        tray.close()

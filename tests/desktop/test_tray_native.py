"""Run with QT_QPA_PLATFORM=cocoa to verify the real AppKit menu."""
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal

from src.desktop.tray import TrayController


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS native menu")
def test_native_menu_actions_translation_and_cleanup(qapp, tmp_path):
    if qapp.platformName() != "cocoa":
        pytest.skip("Requires QT_QPA_PLATFORM=cocoa and a desktop session")

    class Host(QObject):
        state_changed = Signal(dict)
        language_changed = Signal(str)
        language = "pl"
        request_stop = Mock()

    host = Host()
    controller = SimpleNamespace(open_panel=Mock(), quit=Mock())
    tray = TrayController(host, controller, tmp_path)
    try:
        native = tray._native_tray
        assert native.item.menu() == native.menu
        assert native.item.button().image().isTemplate()
        assert tray.tray.contextMenu() is None
        assert not tray.tray.isVisible()
        controller.open_panel.assert_not_called()
        native.menu.performActionForItemAtIndex_(2)
        controller.open_panel.assert_called_once()
        native.menu.performActionForItemAtIndex_(3)
        host.request_stop.assert_called_once()
        host.state_changed.emit({"status": "connected"})
        host.language_changed.emit("en")
        assert native.menu.itemAtIndex_(0).title() == "TikoPlay · Connected"
        assert not native.menu.itemAtIndex_(0).isEnabled()
        assert native.menu.itemAtIndex_(2).title() == "Open panel"
        native.menu.performActionForItemAtIndex_(6)
        controller.quit.assert_called_once()
    finally:
        tray.close()
    assert native.item is None

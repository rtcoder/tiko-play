"""Run on macOS with QT_QPA_PLATFORM=cocoa to exercise native activation."""

import sys
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QSystemTrayIcon

from src.desktop.tray import TrayController


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS activation regression")
@pytest.mark.parametrize("background", [True, False])
def test_background_tray_activates_before_first_menu_click(qapp, qtbot, tmp_path, background):
    if qapp.platformName() != "cocoa":
        pytest.skip("Requires QT_QPA_PLATFORM=cocoa and a desktop session")
    from AppKit import NSApplication

    class Host(QObject):
        state_changed = Signal(dict)

        def request_stop(self):
            pass

    native = NSApplication.sharedApplication()
    old_policy = native.activationPolicy()
    native.setActivationPolicy_(1)  # Accessory: the shipped LSUIElement app.
    host = Host()
    closed = []
    controller = SimpleNamespace(open_panel=lambda: None, quit=lambda: closed.append(True))
    tray = TrayController(host, controller, tmp_path)
    active_when_opened = []
    tray.menu.aboutToShow.connect(
        lambda: active_when_opened.append(bool(native.isActive()))
    )
    try:
        qtbot.wait(300)  # Finish the initial Cocoa application activation.
        if background:
            native.deactivate()
            qtbot.waitUntil(lambda: not native.isActive())
            qtbot.wait(300)
            assert not native.isActive()
        else:
            native.activateIgnoringOtherApps_(True)
            qtbot.waitUntil(lambda: bool(native.isActive()))
        tray.tray.activated.emit(QSystemTrayIcon.ActivationReason.Context)
        qtbot.waitUntil(lambda: tray.menu.isVisible())
        assert active_when_opened == [True]
        action = next(a for a in tray.menu.actions() if a.text() == "Zakończ TikoPlay")
        QTest.mouseClick(
            tray.menu, Qt.MouseButton.LeftButton,
            pos=tray.menu.actionGeometry(action).center(),
        )
        assert closed == [True]
    finally:
        tray.menu.hide()
        tray.close()
        native.setActivationPolicy_(old_policy)

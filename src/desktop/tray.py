import sys
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices, QCursor
from PySide6.QtWidgets import (
    QSystemTrayIcon,
    QMenu,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QApplication,
)
from src.desktop.tray_icon import create_tray_icon


class TrayController:
    def __init__(self, host, controller, data_dir):
        self.tray = QSystemTrayIcon(create_tray_icon())
        self.menu = QMenu()
        self.status = self.menu.addAction("TikoPlay · Zatrzymany")
        self.status.setEnabled(False)
        self.menu.addSeparator()
        self.menu.addAction("Otwórz panel", controller.open_panel)
        self.menu.addAction("Zatrzymaj nasłuch", host.request_stop)
        self.menu.addAction(
            "Otwórz katalog danych",
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir))),
        )
        self.menu.addSeparator()
        self.menu.addAction("Zakończ TikoPlay", controller.quit)
        # QTBUG-147449: native NSMenu tracking on macOS 27 calls clickCount
        # on a non-mouse event and aborts in Qt, before Python can handle it.
        # Keep the menu detached there; show a Qt popup on right click.
        if sys.platform != "darwin":
            self.tray.setContextMenu(self.menu)
        self.tray.setToolTip("TikoPlay — zatrzymany")
        self.controller = controller
        self._menu_position = None
        self._mac_app = (
            QApplication.instance()
            if sys.platform == "darwin" and QApplication.platformName() == "cocoa"
            else None
        )
        if self._mac_app:
            self._mac_app.applicationStateChanged.connect(self._application_state_changed)
        self.tray.activated.connect(self._activated)
        host.state_changed.connect(self._state)
        self.fallback = None
        if self.tray.isSystemTrayAvailable():
            self.tray.show()
        else:
            self.fallback = QWidget()
            self.fallback.setWindowTitle("TikoPlay")
            layout = QVBoxLayout(self.fallback)
            layout.addWidget(QLabel("TikoPlay działa w tle."))
            for text, action in [
                ("Otwórz panel", controller.open_panel),
                ("Zatrzymaj nasłuch", host.request_stop),
                ("Zakończ TikoPlay", controller.quit),
            ]:
                b = QPushButton(text)
                b.clicked.connect(action)
                layout.addWidget(b)
            self.fallback.closeEvent = lambda event: (event.ignore(), controller.quit())
            self.fallback.show()

    def _activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.controller.open_panel()
        elif sys.platform == "darwin" and reason == QSystemTrayIcon.ActivationReason.Context:
            # LSUIElement apps may be inactive when the status item is clicked.
            # Activate before creating the popup: otherwise Cocoa can consume
            # the first menu click as activation instead of triggering its action.
            if self._mac_app:
                from AppKit import NSApplication

                self._menu_position = QCursor.pos()
                native = NSApplication.sharedApplication()
                if native.isActive():
                    self._show_pending_menu()
                else:
                    native.activateIgnoringOtherApps_(True)
            else:
                self.menu.popup(QCursor.pos())

    def _application_state_changed(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            self._show_pending_menu()

    def _show_pending_menu(self):
        if self._menu_position is not None:
            position, self._menu_position = self._menu_position, None
            self.menu.popup(position)

    def _state(self, state):
        labels = {
            "stopped": "Zatrzymany",
            "connecting": "Łączenie",
            "connected": "Połączony",
            "stopping": "Zatrzymywanie",
            "error": "Błąd",
        }
        text = "TikoPlay · " + labels.get(state["status"], state["status"])
        self.status.setText(text)
        self.tray.setToolTip(text)

    def close(self):
        self._menu_position = None
        if self._mac_app:
            self._mac_app.applicationStateChanged.disconnect(self._application_state_changed)
            self._mac_app = None
        self.menu.hide()
        self.tray.hide()
        if self.fallback:
            self.fallback.hide()

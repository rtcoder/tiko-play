import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QCursor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from src.core.i18n import translate
from src.desktop.tray_icon import create_tray_icon


class TrayController:
    def __init__(self, host, controller, data_dir):
        self.language = getattr(host, "language", "pl")
        self._localized = []
        self._status = "stopped"
        self._language_signal = getattr(host, "language_changed", None)
        self.tray = QSystemTrayIcon(create_tray_icon())
        self.menu = QMenu()
        self.status = self.menu.addAction("")
        self.status.setEnabled(False)
        self.menu.addSeparator()
        self._action("Otwórz panel", controller.open_panel)
        self._action("Zatrzymaj nasłuch", host.request_stop)
        self._action(
            "Otwórz katalog danych",
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir))),
        )
        self.menu.addSeparator()
        self._action("Zakończ TikoPlay", controller.quit)
        # QTBUG-147449: native NSMenu tracking on macOS 27 calls clickCount
        # on a non-mouse event and aborts in Qt, before Python can handle it.
        # Keep the menu detached there; show a Qt popup on right click.
        if sys.platform != "darwin":
            self.tray.setContextMenu(self.menu)
        self._state({"status": self._status})
        self.controller = controller
        self._menu_position = None
        self._mac_app = (
            QApplication.instance()
            if sys.platform == "darwin" and QApplication.platformName() == "cocoa"
            else None
        )
        if self._mac_app:
            self._mac_app.applicationStateChanged.connect(
                self._application_state_changed
            )
        self.tray.activated.connect(self._activated)
        host.state_changed.connect(self._state)
        self.fallback = None
        if self.tray.isSystemTrayAvailable():
            self.tray.show()
        else:
            self.fallback = QWidget()
            self.fallback.setWindowTitle("TikoPlay")
            layout = QVBoxLayout(self.fallback)
            label = QLabel()
            self._localized.append((label, "TikoPlay działa w tle."))
            layout.addWidget(label)
            for text, action in [
                ("Otwórz panel", controller.open_panel),
                ("Zatrzymaj nasłuch", host.request_stop),
                ("Zakończ TikoPlay", controller.quit),
            ]:
                b = QPushButton()
                self._localized.append((b, text))
                b.clicked.connect(action)
                layout.addWidget(b)
            self.fallback.closeEvent = lambda event: (event.ignore(), controller.quit())
            self.fallback.show()
        self._retranslate(self.language)
        if self._language_signal is not None:
            self._language_signal.connect(self._retranslate)

    def _action(self, text, callback):
        action = self.menu.addAction(translate(text, self.language), callback)
        self._localized.append((action, text))
        return action

    def _retranslate(self, language):
        self.language = language
        for widget, text in self._localized:
            widget.setText(translate(text, language))
        self._state({"status": self._status})

    def _activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.controller.open_panel()
        elif (
            sys.platform == "darwin"
            and reason == QSystemTrayIcon.ActivationReason.Context
        ):
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
        self._status = state["status"]
        text = "TikoPlay · " + translate(
            labels.get(self._status, self._status), self.language
        )
        self.status.setText(text)
        self.tray.setToolTip(text)

    def close(self):
        if self._language_signal is not None:
            self._language_signal.disconnect(self._retranslate)
            self._language_signal = None
        self._menu_position = None
        if self._mac_app:
            self._mac_app.applicationStateChanged.disconnect(
                self._application_state_changed
            )
            self._mac_app = None
        self.menu.hide()
        self.tray.hide()
        if self.fallback:
            self.fallback.hide()

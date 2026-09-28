import sys

from PySide6.QtCore import QUrl
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
        self._native_tray = None
        self.controller = controller
        if sys.platform == "darwin" and QApplication.platformName() == "cocoa":
            from src.desktop.mac_tray import MacTray

            self._native_tray = MacTray(self.tray.icon(), self.menu.actions())
        elif sys.platform != "darwin":
            self.tray.setContextMenu(self.menu)
        self._state({"status": self._status})
        self.tray.activated.connect(self._activated)
        host.state_changed.connect(self._state)
        self.fallback = None
        if self._native_tray is None and self.tray.isSystemTrayAvailable():
            self.tray.show()
        elif self._native_tray is None:
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
        if reason == QSystemTrayIcon.ActivationReason.Trigger and sys.platform != "darwin":
            self.menu.popup(QCursor.pos())

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
        if self._native_tray is not None:
            self._native_tray.set_tooltip(text)

    def close(self):
        if self._language_signal is not None:
            self._language_signal.disconnect(self._retranslate)
            self._language_signal = None
        if self._native_tray is not None:
            self._native_tray.close()
        self.menu.hide()
        self.tray.hide()
        if self.fallback:
            self.fallback.hide()

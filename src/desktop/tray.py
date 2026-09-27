from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon, QDesktopServices
from PySide6.QtWidgets import (
    QSystemTrayIcon,
    QMenu,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
)
from src.desktop.resources import resource_path


class TrayController:
    def __init__(self, host, controller, data_dir):
        self.tray = QSystemTrayIcon(QIcon(str(resource_path("tiko_play.ico"))))
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
        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip("TikoPlay — zatrzymany")
        self.tray.activated.connect(
            lambda reason: (
                controller.open_panel()
                if reason == QSystemTrayIcon.ActivationReason.Trigger
                else None
            )
        )
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
        self.tray.hide()
        if self.fallback:
            self.fallback.hide()

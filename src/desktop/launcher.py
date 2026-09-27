import argparse
import sys
import webbrowser
from pathlib import Path
from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
from src.desktop.resources import resource_path, user_data_dir
from src.desktop.instance import InstanceGuard
from src.desktop.backend import BackendHost


class LauncherController(QObject):
    url_ready = Signal(str)
    finished = Signal()
    operation_error = Signal(str)

    def __init__(
        self, host, open_browser=webbrowser.open_new_tab, show_error=None, exit_app=None
    ):
        super().__init__()
        self.host = host
        self.open_browser = open_browser
        self.show_error = show_error or (
            lambda text: QMessageBox.warning(None, "TikoPlay", text)
        )
        self.exit_app = exit_app or QApplication.instance().quit
        self.is_ready = False
        self.closing = False
        self.url_ready.connect(self._open_url)
        self.finished.connect(self._finish)
        self.operation_error.connect(self._open_failed)
        host.ready.connect(self._ready)
        host.failed.connect(self._failed)
        self.start_timer = QTimer(self)
        self.start_timer.setSingleShot(True)
        self.start_timer.timeout.connect(self._timeout)
        self.start_timer.start(15000)
        self.close_timer = QTimer(self)
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self._finish)

    def _timeout(self):
        self._failed(
            "Uruchomienie trwa zbyt długo. Spróbuj ponownie uruchomić TikoPlay."
        )

    def _ready(self, origin):
        self.start_timer.stop()
        if self.closing:
            return
        self.is_ready = True
        self.open_panel()

    def open_panel(self):
        if not self.is_ready or self.closing:
            return
        try:
            future = self.host.open_url()

            def complete(f):
                try:
                    self.url_ready.emit(f.result())
                except Exception:
                    self.operation_error.emit(
                        "Nie można otworzyć panelu. Uruchom ponownie TikoPlay."
                    )

            future.add_done_callback(complete)
        except Exception:
            self._open_failed("Panel nie jest jeszcze gotowy.")

    def _open_failed(self, text):
        if not self.closing:
            self.show_error(text)

    def _open_url(self, url):
        if self.closing:
            return
        try:
            if self.open_browser(url) is False:
                raise RuntimeError("browser")
        except Exception:
            QApplication.clipboard().setText(url)
            self.show_error(
                "Nie można otworzyć przeglądarki. Świeży link skopiowano do schowka; wklej go w przeglądarce w ciągu 60 sekund. Możesz też ponowić z ikony TikoPlay."
            )

    def _failed(self, text):
        self.start_timer.stop()
        self.show_error(text)
        self.quit()

    def quit(self):
        if self.closing:
            return
        self.closing = True
        self.start_timer.stop()
        self.host.request_stop()
        self.close_timer.start(5000)
        self.host.shutdown().add_done_callback(lambda _: self.finished.emit())

    def _finish(self):
        self.close_timer.stop()
        self.exit_app()


class DesktopApplication(QApplication):
    controller = None

    # Activation also occurs while interacting with the tray/menu. It must
    # not launch a browser. Explicit tray actions and InstanceGuard handle opens.


def run_desktop():
    parser = argparse.ArgumentParser(description="TikoPlay")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="Osobny katalog danych (testy/wersja przenośna)",
    )
    args = parser.parse_args()
    app = DesktopApplication(sys.argv[:1])
    app.setApplicationName("TikoPlay")
    app.setQuitOnLastWindowClosed(False)
    data = args.data_dir or user_data_dir()
    try:
        guard = InstanceGuard(data)
        if not guard.acquire_or_notify():
            return 0
    except Exception as exc:
        QMessageBox.critical(None, "TikoPlay", str(exc))
        return 1
    host = BackendHost(data, resource_path("frontend/dist"))
    controller = LauncherController(host)
    app.controller = controller
    from src.desktop.tray import TrayController

    tray = TrayController(host, controller, data)
    guard.open_requested.connect(controller.open_panel)
    host.start()
    try:
        return app.exec()
    finally:
        host.shutdown()
        host.thread.join(1)
        guard.close()
        tray.close()

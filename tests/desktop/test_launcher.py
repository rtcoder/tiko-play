from concurrent.futures import Future
from PySide6.QtCore import QObject, Signal
from src.desktop.launcher import LauncherController
from src.desktop.resources import resource_path


class Host(QObject):
    ready = Signal(str)
    failed = Signal(str)
    state_changed = Signal(dict)

    def __init__(self):
        super().__init__()
        self.opened = 0
        self.closed = False

    def open_url(self):
        self.opened += 1
        f = Future()
        f.set_result("http://127.0.0.1:1234/#token=test")
        return f

    def shutdown(self):
        self.closed = True
        f = Future()
        f.set_result(None)
        return f

    def request_stop(self):
        pass


def test_waits_for_ready_and_coalesces_open_requests(qtbot):
    host = Host()
    urls = []
    errors = []
    ctrl = LauncherController(host, urls.append, errors.append, lambda: None)
    ctrl.open_panel()
    ctrl.open_panel()
    assert not urls
    host.ready.emit("http://127.0.0.1:1234")
    qtbot.waitUntil(lambda: len(urls) == 1)
    assert host.opened == 1
    ctrl.open_panel()
    qtbot.waitUntil(lambda: len(urls) == 2)
    ctrl.quit()
    qtbot.waitUntil(lambda: host.closed)


def test_browser_failure_is_reported_without_stopping_backend(qtbot):
    host = Host()
    errors = []
    ctrl = LauncherController(host, lambda u: False, errors.append, lambda: None)
    host.ready.emit("http://127.0.0.1:1234")
    qtbot.waitUntil(lambda: bool(errors))
    assert not host.closed
    ctrl.quit()


def test_resource_path_independent_of_working_directory(tmp_path, monkeypatch):
    import sys

    root = tmp_path / "Tiko Play Żółć"
    root.mkdir()
    (root / "asset").write_text("x")
    monkeypatch.setattr(sys, "_MEIPASS", str(root), raising=False)
    monkeypatch.chdir(tmp_path)
    assert resource_path("asset").read_text() == "x"

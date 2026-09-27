import time
import httpx
from src.desktop.backend import BackendHost


def test_backend_real_http_start_and_shutdown(tmp_path, qtbot):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<html>ok</html>")
    host = BackendHost(tmp_path / "data", static)
    with qtbot.waitSignal(host.ready, timeout=15000):
        host.start()
    origin = host.origin
    assert origin.startswith("http://127.0.0.1:") and not origin.endswith(":0")
    assert httpx.get(origin + "/api/health").json() == {"ready": True}
    url = host.open_url().result(2)
    assert url.startswith(origin + "/#token=")
    host.shutdown().result(5)
    host.thread.join(3)
    assert not host.thread.is_alive()


def test_missing_frontend_reports_failure(tmp_path, qtbot):
    host = BackendHost(tmp_path / "data", tmp_path / "missing")
    with qtbot.waitSignal(host.failed, timeout=5000):
        host.start()
    host.thread.join(3)
    assert not host.thread.is_alive()

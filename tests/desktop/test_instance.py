from pathlib import Path
import subprocess
import sys

from src.desktop.instance import InstanceGuard


def test_second_instance_notifies_owner(tmp_path, qtbot):
    first = InstanceGuard(tmp_path)
    assert first.acquire_or_notify()
    # A real second process keeps the owner's Qt event loop free to accept
    # the connection. Two guards on one thread starve Windows named pipes.
    child = None
    try:
        with qtbot.waitSignal(first.open_requested, timeout=8000):
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "from pathlib import Path; import sys; "
                    "from PySide6.QtCore import QCoreApplication; "
                    "from src.desktop.instance import InstanceGuard; "
                    "app = QCoreApplication([]); "
                    "guard = InstanceGuard(Path(sys.argv[1])); "
                    "sys.exit(1 if guard.acquire_or_notify() else 0)",
                    str(tmp_path),
                ],
                cwd=Path(__file__).resolve().parents[2],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        qtbot.waitUntil(lambda: child.poll() is not None, timeout=8000)
        stdout, stderr = child.communicate()
        assert child.returncode == 0, (stdout, stderr)
    finally:
        if child is not None and child.poll() is None:
            child.kill()
            child.communicate()
        first.close()
    third = InstanceGuard(tmp_path)
    assert third.acquire_or_notify()
    third.close()

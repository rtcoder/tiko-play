import sys


def focus_port():
    if sys.platform == "darwin":
        from src.adapters.focus_macos import MacFocus

        return MacFocus()
    if sys.platform == "win32":
        from src.adapters.focus_windows import WindowsFocus

        return WindowsFocus()
    return UnsupportedFocus()


class UnsupportedFocus:
    def current_target(self):
        return None

    def targets(self):
        raise RuntimeError("Focus unavailable")

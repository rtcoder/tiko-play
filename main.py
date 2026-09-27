import sys
import os

if getattr(sys, "frozen", False):
    base = sys._MEIPASS
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
        base, "PySide6", "Qt", "plugins", "platforms"
    )

if __name__ == "__main__":
    from src.desktop.launcher import run_desktop

    raise SystemExit(run_desktop())

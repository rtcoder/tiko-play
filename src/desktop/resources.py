import os
import sys
from pathlib import Path


def resource_path(relative):
    return (
        Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / relative
    )


def user_data_dir():
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    return base / "TikoPlay"

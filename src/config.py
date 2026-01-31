import json
from pathlib import Path
import sys

APP_NAME = "TikoPlay"


def get_app_dir():
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    elif sys.platform.startswith("win"):
        base = Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home() / ".config"

    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


CONFIG_PATH = get_app_dir() / "config.json"


DEFAULT_CONFIG = {
    "version": 1,
    "show_logs": False,
    "streamer_id": "",
    "target_user": "",
    "mappings": []
}


def load_config():
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = DEFAULT_CONFIG.copy()
    else:
        cfg = DEFAULT_CONFIG.copy()
        save_config(cfg)

    # backward compatibility
    for k, v in DEFAULT_CONFIG.items():
        cfg.setdefault(k, v)

    return cfg


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

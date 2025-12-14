import json
from pathlib import Path

CONFIG_PATH = Path("config.json")

def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    else:
        cfg = {}

    cfg.setdefault("streamer_id", "")
    cfg.setdefault("target_user", "")
    cfg.setdefault("mappings", [])
    cfg.setdefault("show_logs", False)

    return cfg

def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)

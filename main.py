import json
import os
import eel
from tiktok import TikTokListener

CONFIG_FILE = "config.json"
eel.init('web')
listener = TikTokListener()


@eel.expose
def save_settings(settings):
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
        listener.configure(settings)
        return True
    except Exception as e:
        print("Błąd zapisu:", e)
        return False


@eel.expose
def get_settings():
    settings = {
        "streamer_id": "",
        "target_user": "",
        "mappings": {}
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                settings = json.load(f)
                listener.configure(settings)
        except Exception as e:
            print("Błąd odczytu:", e)
    return {
        "streamer_id": settings.get("streamer_id", ""),
        "target_user": settings.get("target_user", ""),
        "mappings": settings.get("mappings", {})
    }


@eel.expose
def get_listener_status():
    return {"running": listener.running}


@eel.expose
def toggle_listening():
    if listener.running:
        listener.stop()
        return {"running": False}
    else:
        if not listener.streamer_id:
            return {"error": "Brak ID streamera"}
        listener.start()
        return {"running": True}


eel.start('index.html', size=(700, 500))

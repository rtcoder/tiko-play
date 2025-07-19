import eel
from tiktok import TikTokListener
import json
import os

CONFIG_FILE = "config.json"

# Inicjalizacja Eel - wskazujemy na folder z plikami interfejsu
eel.init('web')

# Tworzymy jedną, globalną instancję listenera
listener = TikTokListener()

@eel.expose
def save_settings(settings):
    """Zapisuje ustawienia otrzymane z interfejsu i utrwala je w config.json."""
    # 1. Zapisz słownik `settings` bezpośrednio do pliku JSON
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        print(f"Błąd podczas zapisu do pliku {CONFIG_FILE}: {e}")
        return False  # Zwróć informację o błędzie do frontendu

    # 2. Zaktualizuj stan listenera w pamięci (tak jak wcześniej)
    listener.streamer_id = settings.get("streamer_id", "")
    listener.target_user = settings.get("target_user", "")
    listener.key_mapping = settings.get("key_mapping", {})

    print(f"Zapisano ustawienia do {CONFIG_FILE}:", settings)
    return True


@eel.expose
def get_settings():
    """Wczytuje ustawienia z config.json, aktualizuje listenera i zwraca dane do interfejsu."""
    # 1. Spróbuj wczytać konfigurację z pliku
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                settings = json.load(f)

                # 2. Zaktualizuj stan listenera na podstawie wczytanych danych
                listener.streamer_id = settings.get("streamer_id", "")
                listener.target_user = settings.get("target_user", "")
                listener.key_mapping = settings.get("key_mapping", {})
                print(f"Wczytano ustawienia z pliku {CONFIG_FILE}")
        except (json.JSONDecodeError, IOError) as e:
            print(f"Błąd odczytu pliku {CONFIG_FILE}: {e}. Używam domyślnych ustawień.")

    # 3. Zawsze zwracaj aktualny stan listenera do interfejsu
    return {
        "streamer_id": listener.streamer_id,
        "key_mapping": listener.key_mapping,
        "target_user": listener.target_user
    }


@eel.expose
def get_listener_status():
    """Zwraca informację, czy listener jest aktywny."""
    return {"running": listener.running}


@eel.expose
def toggle_listening():
    """Uruchamia lub zatrzymuje nasłuchiwanie."""
    if listener.running:
        listener.stop()
        print("Zatrzymano nasłuchiwanie.")
    else:
        if not listener.streamer_id:
            print("Błąd: Brak ID streamera.")
            return {"error": "Podaj ID streamera przed uruchomieniem."}
        listener.start()
        print("Uruchomiono nasłuchiwanie.")
    return get_listener_status()


# Uruchomienie aplikacji
print("Uruchamianie TikoPlay Web...")
eel.start('index.html', size=(700, 500))
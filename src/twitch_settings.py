"""Public application identity; never put a client secret here."""
import os

TWITCH_CLIENT_ID = ""


def get_twitch_client_id() -> str:
    return os.environ.get("TIKOPLAY_TWITCH_CLIENT_ID", TWITCH_CLIENT_ID).strip()

import time
from collections import OrderedDict
from urllib.parse import urlsplit

from src.core.models import AppError


def protocol_error():
    return AppError(
        "twitch_protocol_error",
        "Niepoprawna odpowiedź czatu Twitcha. Uruchom nasłuch ponownie.",
    )


def validate_reconnect_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        if (
            parsed.scheme != "wss"
            or not (
                host == "eventsub.wss.twitch.tv"
                or host.endswith(".eventsub.wss.twitch.tv")
            )
            or parsed.username
            or parsed.password
            or parsed.port not in (None, 443)
        ):
            raise ValueError()
    except (ValueError, TypeError):
        raise protocol_error() from None
    return url


class SeenMessages:
    def __init__(self, ttl=600, limit=10000, clock=time.monotonic):
        self.ttl, self.limit, self.clock = ttl, limit, clock
        self.events, self.messages = OrderedDict(), OrderedDict()

    def accept(self, event_id, message_id):
        now = self.clock()
        for cache in (self.events, self.messages):
            while cache and next(iter(cache.values())) <= now - self.ttl:
                cache.popitem(last=False)
        if event_id in self.events or message_id in self.messages:
            return False
        for cache, key in ((self.events, event_id), (self.messages, message_id)):
            cache[key] = now
            while len(cache) > self.limit:
                cache.popitem(last=False)
        return True

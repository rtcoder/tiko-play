import pytest

from src.core.models import AppError


def test_duplicate_ids_expire_without_extension_and_cache_is_bounded():
    from src.adapters.twitch_protocol import SeenMessages

    now = [0]
    seen = SeenMessages(ttl=600, limit=2, clock=lambda: now[0])
    assert seen.accept("e1", "m1")
    now[0] = 599
    assert not seen.accept("e2", "m1")
    now[0] = 600
    assert seen.accept("e1", "m1")
    assert seen.accept("e2", "m2") and seen.accept("e3", "m3")
    assert seen.accept("e1", "m1")


@pytest.mark.parametrize(
    "url",
    [
        "ws://eventsub.wss.twitch.tv/ws",
        "wss://eventsub.wss.twitch.tv.evil.com/ws",
        "wss://evil.com",
        "wss://user@eventsub.wss.twitch.tv/ws",
        "wss://eventsub.wss.twitch.tv:8080/ws",
    ],
)
def test_reconnect_rejects_untrusted_url(url):
    from src.adapters.twitch_protocol import validate_reconnect_url

    with pytest.raises(AppError):
        validate_reconnect_url(url)

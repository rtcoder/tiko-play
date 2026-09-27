from src.core.models import AppConfig


def test_factory_routes_channel_without_secrets_in_config():
    from src.adapters.chat import ChatAdapterFactory
    from src.adapters.tiktok import TikTokAdapter
    from src.adapters.twitch import TwitchAdapter

    factory = ChatAdapterFactory(None, None, None)
    a = factory(AppConfig(tiktok={"channel": "alice"}))
    b = factory(AppConfig(platform="twitch", twitch={"channel": "bob"}))
    assert isinstance(a, TikTokAdapter) and a.streamer_id == "alice"
    assert isinstance(b, TwitchAdapter) and b.channel == "bob"

import pytest

from src.core.models import AppError


class Vault:
    def __init__(self):
        self.values = {}

    def get_password(self, service, account):
        return self.values.get((service, account))

    def set_password(self, service, account, value):
        self.values[service, account] = value

    def delete_password(self, service, account):
        self.values.pop((service, account))


async def test_youtube_key_is_separate_from_twitch_and_roundtrips():
    from src.adapters.youtube_key import YouTubeKeyStore

    vault = Vault()
    vault.values["TikoPlay.Twitch", "oauth"] = "existing twitch credentials"
    store = YouTubeKeyStore(backend=vault)
    assert await store.load() is None
    await store.save("my-key")
    assert await store.load() == "my-key"
    await store.delete()
    await store.delete()
    assert await store.load() is None
    assert vault.values["TikoPlay.Twitch", "oauth"] == "existing twitch credentials"


async def test_key_storage_failure_never_echoes_secret():
    from src.adapters.youtube_key import YouTubeKeyStore

    class Broken(Vault):
        def set_password(self, *args):
            raise RuntimeError("my-key")

    with pytest.raises(AppError) as caught:
        await YouTubeKeyStore(backend=Broken()).save("my-key")
    assert caught.value.code == "credential_store_unavailable"
    assert "my-key" not in str(caught.value)

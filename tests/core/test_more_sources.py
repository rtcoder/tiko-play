import json

import pytest
from pydantic import ValidationError

from src.core.config_store import ConfigStore
from src.core.matching import Matcher
from src.core.models import AppConfig


@pytest.mark.parametrize(
    "platform,channel,expected",
    [
        ("youtube", "https://www.youtube.com/watch?v=abcdefghijk&t=30", "abcdefghijk"),
        ("youtube", "https://youtu.be/abcdefghijk?si=test", "abcdefghijk"),
        ("youtube", "https://youtube.com/live/abcdefghijk", "abcdefghijk"),
        ("youtube", "abcdefghijk", "abcdefghijk"),
        ("kick", "@Some-Streamer", "some-streamer"),
    ],
)
def test_new_source_selects_and_normalizes_its_own_channel(platform, channel, expected):
    cfg = AppConfig(platform=platform, **{platform: {"channel": channel}})
    assert cfg.active_source().channel == expected
    assert cfg.tiktok.channel == cfg.twitch.channel == ""


@pytest.mark.parametrize(
    "platform,channel",
    [
        ("youtube", "https://evil.test/watch?v=abcdefghijk"),
        ("youtube", "https://youtube.com.evil.test/watch?v=abcdefghijk"),
        ("youtube", "https://evil@youtube.com/watch?v=abcdefghijk"),
        ("youtube", "@channel"),
        ("youtube", "short"),
        ("kick", "../foo"),
        ("kick", "https://kick.com/foo"),
    ],
)
def test_invalid_source_is_rejected_before_network(platform, channel):
    with pytest.raises(ValidationError):
        AppConfig(platform=platform, **{platform: {"channel": channel}})


@pytest.mark.parametrize("version", [1, 2, 3])
async def test_upgrade_keeps_old_sources_and_backup(tmp_path, version):
    data = {
        "version": version,
        "mappings": [{"id": "m", "trigger": "go", "keys": ["a"]}],
        "custom": "kept",
    }
    if version == 3:
        data.update(
            platform="twitch",
            tiktok={"channel": "alice"},
            twitch={"channel": "bob", "target_user": "carol"},
        )
    else:
        data.update(streamer_id="alice", target_user="carol")
    path = tmp_path / "config.json"
    original = json.dumps(data).encode()
    path.write_bytes(original)
    cfg = (await ConfigStore(path).load()).config
    assert cfg.version == 7
    assert cfg.youtube.channel == cfg.kick.channel == ""
    assert cfg.mappings[0].id == "m" and cfg.model_dump()["custom"] == "kept"
    assert path.with_name(f"config.v{version}.backup.json").read_bytes() == original
    if version == 3:
        assert cfg.platform == "twitch" and cfg.twitch.target_user == "carol"
    else:
        assert cfg.platform == "tiktok" and cfg.tiktok.target_user == "carol"
    assert (await ConfigStore(path).load()).config == cfg


def test_kick_filters_login_case_insensitively_youtube_uses_exact_channel_ids():
    rule = [{"id": "m", "trigger": "go", "keys": ["a"]}]
    kick = Matcher(
        AppConfig(platform="kick", kick={"target_user": "@Alice"}, mappings=rule)
    )
    assert kick.match("alice", "go") == ("a",)
    youtube = Matcher(
        AppConfig(platform="youtube", youtube={"target_user": "UCAbc"}, mappings=rule)
    )
    assert youtube.match("ucabc", "go") is None
    assert youtube.match("UCAbc", "go") == ("a",)

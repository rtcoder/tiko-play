import json


import pytest

from src.core.config_store import ConfigStore
from src.core.models import AppConfig, AppError
from src.core.matching import Matcher
from src.core.presets import get_presets


async def test_v4_migrates_to_one_profile_and_keeps_original(tmp_path):
    path = tmp_path / "config.json"
    original = json.dumps(
        {
            "version": 4,
            "platform": "twitch",
            "twitch": {"channel": "alice", "target_user": "bob"},
            "mappings": [{"id": "existing", "trigger": "go", "keys": ["left"]}],
        }
    )
    path.write_text(original)
    config = (await ConfigStore(path).load()).config
    assert config.version == 7
    assert len(config.profiles) == 1
    assert config.active_profile.name == "Domyślny"
    assert config.active_profile.filters.twitch == "bob"
    assert config.mappings[0].id == "existing"
    assert config.twitch.channel == "alice"
    assert (tmp_path / "config.v4.backup.json").read_text() == original
    assert (await ConfigStore(path).load()).config == config


def test_active_profile_drives_matching_and_filters():
    config = AppConfig(
        profiles=[
            {
                "id": "a",
                "name": "A",
                "filters": {"tiktok": "alice"},
                "mappings": [{"id": "x", "trigger": "go", "keys": ["left"]}],
            },
            {
                "id": "b",
                "name": "B",
                "filters": {"tiktok": "bob"},
                "mappings": [{"id": "y", "trigger": "go", "keys": ["right"]}],
            },
        ],
        active_profile_id="b",
    )
    matcher = Matcher(config)
    assert matcher.match("alice", "go") is None
    assert matcher.match("bob", "go") == ("right",)


@pytest.mark.parametrize(
    "profiles,active",
    [
        ([], "x"),
        ([{"id": "a", "name": "A"}], "missing"),
        ([{"id": "a", "name": "A"}, {"id": "a", "name": "B"}], "a"),
        ([{"id": "a", "name": "   "}], "a"),
    ],
)
def test_invalid_profile_collection_rejected(profiles, active):
    with pytest.raises(ValueError):
        AppConfig(profiles=profiles, active_profile_id=active)


def test_numpad_2468_is_available_without_removing_existing_presets():
    presets = get_presets()
    assert {m["trigger"]: m["keys"] for m in presets["NumPad 2468"]} == {
        "2": ["down"],
        "4": ["left"],
        "6": ["right"],
        "8": ["up"],
    }
    assert "WASD (klasyczne)" in presets


def test_export_import_uses_allowlist_and_fresh_ids():
    from src.core.profiles import export_profile, import_profile

    config = AppConfig(
        mappings=[{"id": "old", "trigger": "go", "keys": ["left"], "token": "secret"}],
        tiktok={"target_user": "private"},
    )
    payload = export_profile(config.active_profile)
    assert "private" not in json.dumps(payload)
    assert "secret" not in json.dumps(payload)
    new = import_profile(payload)
    assert new.id != config.active_profile.id
    assert new.mappings[0].id != "old"
    assert new.filters.tiktok == ""
    assert new.mappings[0].keys == ("left",)


def test_import_rejects_future_version_and_limits():
    from src.core.profiles import import_profile

    for payload in (
        {"format_version": 3, "name": "x", "mappings": []},
        {
            "format_version": 1,
            "name": "x",
            "mappings": [{"trigger": str(i), "keys": ["a"]} for i in range(501)],
        },
    ):
        with pytest.raises(AppError):
            import_profile(payload)


def test_templates_are_valid_and_numpad_resolves_to_arrows():
    from src.core.profile_templates import get_profile_templates
    from src.core.profiles import import_profile

    for template in get_profile_templates():
        profile = import_profile(
            {
                "format_version": 1,
                "name": template["name"],
                "mappings": template["mappings"],
            }
        )
        assert profile.mappings
        if template["id"] == "numpad":
            cfg = AppConfig(profiles=[profile], active_profile_id=profile.id)
            matcher = Matcher(cfg)
            assert matcher.match("viewer", "2") == ("down",)
            assert matcher.match("viewer", "4") == ("left",)
            assert matcher.match("viewer", "6") == ("right",)
            assert matcher.match("viewer", "8") == ("up",)


async def test_failed_profile_write_preserves_collection_and_selection(
    tmp_path, monkeypatch
):
    store = ConfigStore(tmp_path / "config.json")
    old = await store.load()
    original = store.path.read_bytes()
    config = AppConfig(
        profiles=[{"id": "next", "name": "Next"}], active_profile_id="next"
    )

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr("src.core.config_store.os.replace", fail)
    with pytest.raises(AppError):
        await store.save(config, old.revision)
    assert store.snapshot() == old
    assert store.path.read_bytes() == original


async def test_migration_preserves_large_existing_profile(tmp_path):
    path = tmp_path / "config.json"
    mappings = [{"id": str(i), "trigger": str(i), "keys": ["a"]} for i in range(501)]
    path.write_text(json.dumps({"version": 4, "mappings": mappings}))
    config = (await ConfigStore(path).load()).config
    assert len(config.mappings) == 501

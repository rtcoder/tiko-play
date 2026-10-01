import pytest
from pydantic import ValidationError

from src.core.actions import ActionDefinition
from src.core.models import Mapping
from src.core.profiles import export_profile, import_profile


def test_legacy_mapping_becomes_one_press():
    m = Mapping(id="m", trigger="go", keys=["ctrl", "a"])
    assert m.action.steps[0].type == "press"
    assert m.action.steps[0].keys == ("ctrl", "a")
    assert "keys" not in m.model_dump()
    assert m.model_dump()["action"]["steps"][0]["keys"] == ("ctrl", "a")


@pytest.mark.parametrize(
    "steps",
    [
        [],
        [{"type": "hold", "keys": ["a"], "duration_ms": 49}],
        [{"type": "wait", "duration_ms": 3001}],
        [{"type": "press", "keys": []}],
        [{"type": "press", "keys": ["not-a-key"]}],
        [{"type": "wait", "duration_ms": 10}] * 21,
        [{"type": "wait", "duration_ms": 3000}] * 4,
        [{"type": "wait", "duration_ms": True}],
        [{"type": "wait", "duration_ms": 10.5}],
    ],
)
def test_action_rejects_invalid_steps(steps):
    with pytest.raises(ValidationError):
        ActionDefinition(steps=steps)


def test_sequence_portable_roundtrip_and_legacy_import():
    profile = import_profile(
        {
            "format_version": 1,
            "name": "Old",
            "mappings": [{"trigger": "go", "keys": ["a"]}],
        }
    )
    payload = export_profile(profile)
    assert payload["format_version"] == 3
    assert payload["mappings"][0]["action"]["steps"][0]["type"] == "press"
    payload["mappings"][0]["action"]["steps"] += [
        {"type": "wait", "duration_ms": 50},
        {"type": "hold", "keys": ["left"], "duration_ms": 100},
    ]
    assert len(import_profile(payload).mappings[0].action.steps) == 3


async def test_v5_migration_keeps_profiles_and_raw_backup(tmp_path):
    import json

    from src.core.config_store import ConfigStore

    path = tmp_path / "config.json"
    raw = json.dumps(
        {
            "version": 5,
            "active_profile_id": "p",
            "profiles": [
                {
                    "id": "p",
                    "name": "Retro",
                    "filters": {"tiktok": "alice"},
                    "mappings": [
                        {"id": "m", "trigger": "go", "keys": ["ctrl", "a"], "note": 42}
                    ],
                }
            ],
        }
    ).encode()
    path.write_bytes(raw)
    config = (await ConfigStore(path).load()).config
    assert config.version == 7
    assert config.active_profile_id == "p"
    assert config.active_profile.filters.tiktok == "alice"
    assert config.mappings[0].id == "m"
    assert config.mappings[0].action.steps[0].keys == ("ctrl", "a")
    assert config.mappings[0].model_dump()["note"] == 42
    assert (tmp_path / "config.v5.backup.json").read_bytes() == raw
    assert (await ConfigStore(path).load()).config == config

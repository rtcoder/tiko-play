import json
import pytest
from src.core.config_store import ConfigStore
from src.core.models import AppConfig, AppError


async def test_migration_backup_and_stable_ids(tmp_path):
    p = tmp_path / "config.json"
    original = json.dumps(
        {
            "version": 1,
            "custom": "kept",
            "mappings": [{"trigger": "x", "keys": ["ctrl", "a"]}],
        }
    ).encode()
    p.write_bytes(original)
    s = ConfigStore(p)
    a = await s.load()
    assert a.config.version == 2 and a.config.mappings[0].keys == ("ctrl", "a")
    assert a.config.model_dump()["custom"] == "kept"
    assert p.with_name("config.v1.backup.json").read_bytes() == original
    b = await ConfigStore(p).load()
    assert a.config.mappings[0].id == b.config.mappings[0].id


async def test_conflict_and_failed_replace(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    s = ConfigStore(p)
    a = await s.load()
    b = await s.save(AppConfig(streamer_id="alice"), a.revision)
    with pytest.raises(AppError) as e:
        await s.save(AppConfig(), a.revision)
    assert e.value.code == "revision_conflict"
    old = p.read_bytes()

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr("src.core.config_store.os.replace", fail)
    with pytest.raises(AppError):
        await s.save(AppConfig(streamer_id="bob"), b.revision)
    assert p.read_bytes() == old and s.snapshot() == b


@pytest.mark.parametrize(
    "raw",
    [b"{broken", b"[]", b'{"version":99}', b'{"mappings":[{"trigger":"","keys":[]}]}'],
)
async def test_invalid_data_never_silently_overwritten(tmp_path, raw):
    p = tmp_path / "config.json"
    p.write_bytes(raw)
    s = ConfigStore(p)
    with pytest.raises(AppError):
        await s.load()
    assert p.read_bytes() == raw
    if b"99" in raw:
        with pytest.raises(AppError):
            await s.repair(AppConfig())
    else:
        await s.repair(AppConfig())
        assert list(tmp_path.glob("config.recovery.*.json"))[0].read_bytes() == raw

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
    assert a.config.version == 4 and a.config.mappings[0].keys == ("ctrl", "a")
    assert a.config.model_dump()["custom"] == "kept"
    assert p.with_name("config.v1.backup.json").read_bytes() == original
    b = await ConfigStore(p).load()
    assert a.config.mappings[0].id == b.config.mappings[0].id


async def test_conflict_and_failed_replace(tmp_path, monkeypatch):
    p = tmp_path / "config.json"
    s = ConfigStore(p)
    a = await s.load()
    b = await s.save(AppConfig(tiktok={"channel":"alice"}), a.revision)
    with pytest.raises(AppError) as e:
        await s.save(AppConfig(), a.revision)
    assert e.value.code == "revision_conflict"
    old = p.read_bytes()

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr("src.core.config_store.os.replace", fail)
    with pytest.raises(AppError):
        await s.save(AppConfig(tiktok={"channel":"bob"}), b.revision)
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


@pytest.mark.parametrize("version", [1, 2])
async def test_existing_user_and_multiple_users_survive_reload(tmp_path, version):
    from src.core.users import allowed_users
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"version": version, "target_user": "alice"}))
    store = ConfigStore(p)
    initial = await store.load()
    assert allowed_users(initial.config.tiktok.target_user) == {"alice"}
    users = "@alice, bob\ncarol"
    await store.save(AppConfig(tiktok={"target_user":users}), initial.revision)
    restored = await ConfigStore(p).load()
    assert restored.config.tiktok.target_user == users
    assert allowed_users(restored.config.tiktok.target_user) == {"alice", "bob", "carol"}


@pytest.mark.parametrize('version', [1, 2])
async def test_v4_migration_preserves_source_and_backup_collision(tmp_path, version):
    p = tmp_path / 'config.json'
    raw = json.dumps({'version': version, 'streamer_id': '@Alice', 'target_user': 'Bob', 'custom': 42}).encode()
    p.write_bytes(raw)
    old = tmp_path / f'config.v{version}.backup.json'
    old.write_bytes(b'older backup')
    cfg = (await ConfigStore(p).load()).config
    assert cfg.version == 4
    assert cfg.platform == 'tiktok'
    assert cfg.tiktok.channel == 'Alice'
    assert cfg.tiktok.target_user == 'Bob'
    assert cfg.twitch.channel == ''
    assert cfg.model_dump()['custom'] == 42
    assert 'streamer_id' not in cfg.model_dump()
    assert old.read_bytes() == b'older backup'
    assert list(tmp_path.glob(f'config.v{version}.backup.*.json'))[0].read_bytes() == raw


async def test_migration_backup_failure_keeps_original(tmp_path, monkeypatch):
    from pathlib import Path
    p = tmp_path / 'config.json'
    p.write_text('{"version":2,"streamer_id":"alice"}')
    raw = p.read_bytes()
    original_open = Path.open
    def fail_backup(self, mode='r', *args, **kwargs):
        if mode == 'xb':
            raise OSError('disk full')
        return original_open(self, mode, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', fail_backup)
    with pytest.raises(AppError):
        await ConfigStore(p).load()
    assert p.read_bytes() == raw

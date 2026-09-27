import pytest
from pathlib import Path
from packaging_support import validate_assets


def test_missing_frontend_rejected(tmp_path):
    with pytest.raises(RuntimeError):
        validate_assets(tmp_path)
    (tmp_path / "frontend/dist").mkdir(parents=True)
    (tmp_path / "frontend/dist/index.html").write_text(
        '<script src="/assets/x.js"></script>'
    )
    with pytest.raises(RuntimeError):
        validate_assets(tmp_path)
    (tmp_path / "frontend/dist/assets").mkdir()
    (tmp_path / "frontend/dist/assets/x.js").write_text("ok")
    for name in ("tiko_play.ico", "tiko_play.icns"):
        (tmp_path / name).write_bytes(b"icon")
    assets = validate_assets(tmp_path)
    assert not any("config.json" in str(source) for source, target in assets)

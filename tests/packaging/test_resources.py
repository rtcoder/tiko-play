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


@pytest.mark.parametrize('platform,native',[('macos','keyring.backends.macOS'),('windows','keyring.backends.Windows')])
def test_bundle_includes_native_vault_and_transport(tmp_path, monkeypatch, platform, native):
    import runpy
    import sys
    from types import SimpleNamespace
    # Execute the real spec with an instrumented bundler, no actual build in unit tests.
    root=Path(__file__).resolve().parents[2]
    observed={}
    def analysis(*args,**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(pure=[],scripts=[],binaries=[],datas=kwargs['datas'])
    monkeypatch.setattr('packaging_support.validate_assets',lambda _: [('panel','frontend/dist')])
    monkeypatch.setitem(sys.modules,'PyInstaller.utils.hooks',SimpleNamespace(collect_submodules=lambda name:[name]))
    runpy.run_path(str(root/'packaging'/f'{platform}.spec'),init_globals={
        'SPECPATH':str(root/'packaging'),'Analysis':analysis,
        **{name:lambda *args,**kwargs:None for name in ('PYZ','EXE','COLLECT','BUNDLE')}
    })
    assert native in observed['hiddenimports']
    assert 'httpx' in observed['hiddenimports']
    assert 'websockets.asyncio.client' in observed['hiddenimports']
    assert not any('config.json' in str(source) for source,_ in observed['datas'])

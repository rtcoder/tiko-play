from pathlib import Path
import sys
root=Path(SPECPATH).parent
sys.path.insert(0,str(root))
from packaging_support import validate_assets
from PyInstaller.utils.hooks import collect_submodules

a=Analysis([str(root/'main.py')],pathex=[str(root)],datas=validate_assets(root),hiddenimports=collect_submodules('TikTokLive')+['keyring.backends.macOS','httpx','websockets.asyncio.client','uvicorn.logging','uvicorn.loops.asyncio','uvicorn.protocols.http.h11_impl','uvicorn.protocols.websockets.websockets_sansio_impl','uvicorn.lifespan.on'],excludes=['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtQml','tkinter'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='TikoPlay',console=False,icon=str(root/'tiko_play.icns'))
coll=COLLECT(exe,a.binaries,a.datas,name='TikoPlay')
app=BUNDLE(coll,name='TikoPlay.app',icon=str(root/'tiko_play.icns'),bundle_identifier='com.tikoplay.app',info_plist={'CFBundleShortVersionString':'2.0.0','NSHighResolutionCapable':True,'LSUIElement':True})

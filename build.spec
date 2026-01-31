# build.spec
# PyInstaller spec for TikoPlay

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
    ],
    hiddenimports=[
        'TikTokLive',
        'TikTokLive.client',
        'TikTokLive.events',
        'pyautogui',
        'pynput',
        'asyncio',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TikoPlay',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='tiko_play.ico'
)

app = BUNDLE(
    exe,
    name="TikoPlay.app",
    icon='tiko_play.icns',
    bundle_identifier="com.tikoplay.app",
)



# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['src/doppkit/gui.py'],
    pathex=['resources'],
    binaries=[],
    datas=[],
    hiddenimports=['doppkit.resources'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "rich",
        "matplotlib",
        "pygments",
        "PIL"
    ],
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
    name='doppkit',
    debug=False,
    bootloader_ignore_signals=False,
    exclude_binaries=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="src\\doppkit\\resources\\grid-icon.ico"
)

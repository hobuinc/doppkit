# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(
    ['src/doppkit/gui/__main__.py'],
    pathex=['resources'],
    binaries=[],
    datas=[("src/doppkit/gui/resources", "doppkit/gui/resources")],
    hiddenimports=['doppkit.gui.resources'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "rich",
        "matplotlib",
        "pygments",
        "PIL",
        "click"
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
    name='doppkit-gui',
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
    icon="src/doppkit/gui/resources/grid-icon.ico",
    manifest="doppkit.manifest"
)

# the following config is for making a non one-file binary
# which is useful for debugging purposes
# exe = EXE(
#     pyz,
#     a.scripts,
#     [],
#     exclude_binaries=True,
#     name="doppkit",
#     debug=True,
#     bootloader_ignore_signals=False,
#     strip=False,
#     upx=True,
#     console=True,
#     disable_windowed_traceback=False,
#     argv_emulation=False,
#     target_arch=None,
#     codesign_identity=None,
#     entitlemens_file=None
# )
#
# coll = COLLECT(
#     exe,
#     a.binaries,
#     a.zipfiles,
#     a.datas,
#     strip=False,
#     upx=True,
#     upx_exclude=[],
#     name="doppkit"
# )

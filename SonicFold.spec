# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['desktop.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static'), ('100 pdb with chemmical shift values .csv', '.'), ('6188_simulated_hsqc_backbone_example_music.csv', '.'), ('TimGM6mb.sf2', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SonicFold',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SonicFold',
)
app = BUNDLE(
    coll,
    name='SonicFold.app',
    icon='icon.icns',
    bundle_identifier=None,
)

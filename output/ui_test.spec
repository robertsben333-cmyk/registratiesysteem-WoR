# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('c:\\Users\\XavierFriesen\\.projects SFNL\\registratiesysteem WoR\\app\\templates', 'app\\templates'), ('c:\\Users\\XavierFriesen\\.projects SFNL\\registratiesysteem WoR\\app\\static', 'app\\static'), ('c:\\Users\\XavierFriesen\\.projects SFNL\\registratiesysteem WoR\\latest.json', '.')],
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
    name='ui_test',
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
    icon=['c:\\Users\\XavierFriesen\\.projects SFNL\\registratiesysteem WoR\\assets\\wor-logo.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ui_test',
)

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

qt6_data = collect_data_files('PyQt6', subdir=None, include_py_files=True)

a = Analysis(
    ['ui.py'],
    pathex=[],
    binaries=[],
    datas=qt6_data,
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'importlib',
        'importlib.resources',
        'datetime',
        'msgpack',
        'json',
        'os',
        'sys',
        'platform',
        'uuid',
        'typing',
        'sqlite3',
        're',
        'inspect',
        'asyncio',
        'importlib.util',
        'chardet',
        '__future__',
        'difflib',
        'pydoc',
        'filecmp',
        'traceback'
        ],
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
    name='ui',
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
    name='ui',
)

# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


datas = collect_data_files("Cython") + collect_data_files("paddleocr", include_py_files=True)
binaries = collect_dynamic_libs("paddle")
hiddenimports = [
    "paddleocr",
    "paddle",
    "cv2",
    "PIL",
    "requests",
    "yaml",
    "numpy",
    "tqdm",
    "shapely",
    "pyclipper",
    "lmdb",
    "rapidfuzz",
    "docx",
    "bs4",
    "lxml",
    "skimage",
    "scipy",
    "albumentations",
    "albucore",
    "pydantic",
] + collect_submodules("skimage") + collect_submodules("albumentations")


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["paddle.jit.sot"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="photosign",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

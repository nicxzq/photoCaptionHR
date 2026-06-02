# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


datas = collect_data_files("Cython") + collect_data_files("paddleocr", include_py_files=True) + [("models", "models")]
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
] + collect_submodules("skimage", filter=lambda name: ".tests" not in name) + collect_submodules(
    "albumentations", filter=lambda name: ".tests" not in name
)


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

splash = Splash(
    "assets/splash.png",
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(32, 238),
    text_size=10,
    text_font="Segoe UI",
    text_color="#6E6E73",
    text_default="正在启动 PhotoSign，请稍候...",
    always_on_top=True,
)

exe = EXE(
    pyz,
    splash,
    a.scripts,
    a.binaries,
    a.datas,
    splash.binaries,
    [],
    name="photosign",
    debug=False,
    bootloader_ignore_signals=False,
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
)

cli = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="photosign-cli",
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

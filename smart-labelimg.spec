# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path


root = Path.cwd()
datas = []
mobile_sam_checkpoint = root / "models" / "mobile_sam.pt"
if not mobile_sam_checkpoint.exists():
    raise SystemExit("models/mobile_sam.pt is required for the macOS release build")
datas.append((str(mobile_sam_checkpoint), "models"))
app_icon = None
if sys.platform == "darwin":
    app_icon = root / "assets" / "AppIcon.icns"
    if not app_icon.exists():
        raise SystemExit("assets/AppIcon.icns is required for the macOS release build")


a = Analysis(
    ["smart_labelimg/app.py"],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "datasets",
        "IPython",
        "jupyterlab",
        "matplotlib",
        "nltk",
        "notebook",
        "onnxruntime",
        "pandas",
        "pyarrow",
        "pytest",
        "scipy",
        "sklearn",
        "spacy",
        "tensorflow",
        "tkinter",
        "torchaudio",
        "transformers",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Smart LabelImg",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="arm64" if sys.platform == "darwin" else None,
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
    name="Smart LabelImg",
)
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="Smart LabelImg.app",
        icon=str(app_icon),
        bundle_identifier="com.smartlabelimg.app",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleDisplayName": "Smart LabelImg",
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "LSMinimumSystemVersion": "12.0",
        },
    )

# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


project_root = Path(SPEC).resolve().parents[1]
src_root = project_root / "src"
sys.path.insert(0, str(src_root))

datas = collect_data_files("playwright")

playwright_browsers_archive = project_root / ".playwright-browsers.zip"
if not playwright_browsers_archive.exists():
    raise SystemExit(
        "Bundled Playwright browser archive was not found at .playwright-browsers.zip. "
        "Run `python scripts/build_executable.py` first."
    )

datas += [
    (str(project_root / "config"), "config"),
    (str(src_root / "bi_validator" / "templates"), "bi_validator/templates"),
    (str(playwright_browsers_archive), "."),
]

a = Analysis(
    [str(src_root / "bi_validator" / "launcher.py")],
    pathex=[str(src_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "IPython",
        "grpc",
        "jupyter_client",
        "jupyter_core",
        "lxml",
        "matplotlib",
        "notebook",
        "numpy",
        "openpyxl",
        "pandas",
        "pyarrow",
        "pytest",
        "tkinter",
        "zmq",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="bi-dashboard-validator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

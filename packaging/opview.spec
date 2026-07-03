# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for OPView (onedir).

Invoked by the root CMakeLists.txt, which provides OPVIEW_VERSION_FILE in the
environment (path to a version.txt written into the build tree).
"""

import os
from pathlib import Path

SRC = Path(SPECPATH).parent  # repo root (this spec lives in packaging/)

version_file = os.environ["OPVIEW_VERSION_FILE"]

datas = [
    (str(SRC / "assets"), "assets"),
    (str(SRC / "doc"), "doc"),
    (version_file, "."),  # -> _internal/version.txt == app.resources.ROOT_DIR/version.txt
]

hiddenimports = [
    "vtkmodules.all",
    "vtkmodules.util.numpy_support",
    "vtkmodules.util.data_model",
    "vtkmodules.util.execution_model",
]

a = Analysis(
    [str(SRC / "main.py")],
    pathex=[str(SRC)],
    datas=datas,
    hiddenimports=hiddenimports,
    hooksconfig={"matplotlib": {"backends": "QtAgg"}},
    excludes=["tkinter", "PyQt5", "PyQt6", "IPython", "jupyter", "pytest"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="OPView",
    console=False,
    icon=str(SRC / "assets" / "OPView.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="OPView",
)

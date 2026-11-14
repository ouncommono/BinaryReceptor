"""Automated build script for BinaryReceptor v3.2.0.

Compiles the application into an ultra-lightweight standalone Windows .exe using PyInstaller
with aggressive DLL stripping, module exclusions, and UPX compression:
  - Excludes unused modules (tkinter, unittest, numpy, matplotlib, QtNetwork, QtQuick, QtPdf, etc.)
  - Strips massive unused binaries (opengl32sw.dll [~21MB], d3dcompiler_47.dll [~4.5MB], unused imageformat plugins)
  - Windowed GUI mode (--noconsole, single executable)
  - Native Windows PE version metadata (res/version.txt) and multi-resolution icon (assets/icon.ico)
  - Automatically copies default settings.ini alongside BinaryReceptor.exe in dist/
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
BUILD_DIR = ROOT_DIR / "build"
ASSETS_DIR = ROOT_DIR / "assets"
ICON_PATH = ASSETS_DIR / "icon.ico"
VERSION_FILE = ROOT_DIR / "res" / "version.txt"
SPEC_FILE = ROOT_DIR / "BinaryReceptor.spec"

EXCLUDE_MODULES = [
    "tkinter", "unittest", "pydoc", "doctest", "sqlite3", "xmlrpc",
    "multiprocessing", "distutils", "setuptools", "pkg_resources",
    "numpy", "scipy", "pandas", "matplotlib",
    "PIL.ImageTk", "PIL.ImageQt", "cryptography", "OpenSSL",
    "asyncio", "email", "html.parser", "http.cookiejar",
    "pdb", "inspect", "difflib",
    "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtOpenGL",
    "PySide6.QtOpenGLWidgets", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtSensors",
    "PySide6.QtSvgWidgets", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtUiTools", "PySide6.Qt3D", "PySide6.QtCharts",
]


def clean():
    print("[1/5] Cleaning prior build artifacts...")
    for folder in [DIST_DIR, BUILD_DIR]:
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)
    if SPEC_FILE.exists():
        try:
            SPEC_FILE.unlink()
        except OSError:
            pass


def ensure_icon():
    print("[2/5] Verifying multi-resolution application icons...")
    sys.path.insert(0, str(ROOT_DIR))
    from src.ui.icon_gen import ensure_icons_exist
    ensure_icons_exist()


def generate_spec_file() -> None:
    print("[3/5] Generating optimized PyInstaller .spec configuration...")
    root_str = str(ROOT_DIR).replace("\\", "/")
    excludes_repr = repr(EXCLUDE_MODULES)

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT_DIR = Path(r'{root_str}')
ASSETS_DIR = ROOT_DIR / 'assets'
VERSION_FILE = ROOT_DIR / 'res' / 'version.txt'

a = Analysis(
    [str(ROOT_DIR / 'src' / 'main.py')],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[(str(ASSETS_DIR), 'assets')],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'qrcode',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes={excludes_repr},
    noarchive=False,
    optimize=2,
)

# Strip massive unused DLLs and image plugins
STRIP_BINARIES = {{
    'opengl32sw.dll',
    'd3dcompiler_47.dll',
    'qt6network.dll',
    'qt6qml.dll',
    'qt6qmlmodels.dll',
    'qt6quick.dll',
    'qt6pdf.dll',
    'qt6pdfwidgets.dll',
    'qt6opengl.dll',
    'qt6openglwidgets.dll',
    'qt6virtualkeyboard.dll',
    'qtiff.dll',
    'qwebp.dll',
    'qicns.dll',
    'qtga.dll',
    'qpdf.dll',
    'qgif.dll',
}}

filtered_binaries = []
for entry in a.binaries:
    name = entry[0]
    basename = Path(name).name.lower()
    if basename in STRIP_BINARIES:
        continue
    if any(k in basename for k in ['qt6network', 'qt6quick', 'qt6qml', 'qt6pdf', 'qt6opengl']):
        continue
    filtered_binaries.append(entry)
a.binaries = filtered_binaries

# Strip unused translations
filtered_datas = []
for entry in a.datas:
    dest = entry[0].lower()
    if 'translations' in dest and not dest.endswith('_en.qm'):
        continue
    filtered_datas.append(entry)
a.datas = filtered_datas

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='BinaryReceptor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=['vcruntime140.dll', 'python3*.dll'],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
    icon=str(ASSETS_DIR / 'icon.ico'),
)
"""
    SPEC_FILE.write_text(spec_content, encoding="utf-8")


def run_pyinstaller():
    print("[4/5] Executing PyInstaller build with aggressive size optimization...")
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ]
    print("Command:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if proc.returncode != 0:
        print("[ERROR] PyInstaller compilation failed with code:", proc.returncode)
        sys.exit(proc.returncode)


def finalize_release_bundle():
    print("[5/5] Finalizing distribution bundle...")
    exe_path = DIST_DIR / "BinaryReceptor.exe"
    if not exe_path.exists():
        print("[ERROR] Expected binary not found:", exe_path)
        sys.exit(1)

    # Write clean default settings.ini alongside BinaryReceptor.exe
    sys.path.insert(0, str(ROOT_DIR))
    from src.config import DEFAULT_SETTINGS_INI
    target_ini = DIST_DIR / "settings.ini"
    target_ini.write_text(DEFAULT_SETTINGS_INI, encoding="utf-8")

    size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"[DONE] Build SUCCESSFUL!")
    print(f"       Executable : {exe_path} ({size_mb:.2f} MB)")
    print(f"       Settings   : {target_ini}")


def main():
    clean()
    ensure_icon()
    generate_spec_file()
    run_pyinstaller()
    finalize_release_bundle()


if __name__ == "__main__":
    main()

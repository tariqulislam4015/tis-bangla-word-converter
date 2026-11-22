# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — folder ("onedir") build used by the Windows installer.
# Build from the project root:   pyinstaller --noconfirm packaging/tis_installer.spec
import os

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
NAME = "TIS_Bangla_Word_Converter"

datas = [
    (os.path.join(ROOT, "assets", "icons"), os.path.join("assets", "icons")),
    (os.path.join(ROOT, "assets", "images"), os.path.join("assets", "images")),
    (os.path.join(ROOT, "assets", "audio"), os.path.join("assets", "audio")),
    (os.path.join(ROOT, "LICENSE"), "."),
]

# Qt modules TIS never uses: excluding them keeps the build small.
EXCLUDES = [
    "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuickWidgets", "PySide6.Qt3DCore",
    "PySide6.Qt3DRender", "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtNetworkAuth", "PySide6.QtWebSockets", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtOpenGL", "PySide6.QtOpenGLWidgets", "PySide6.QtSql", "PySide6.QtTest",
]

a = Analysis(
    [os.path.join(ROOT, "main.py")],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=["PySide6.QtSvg"],
    hookspath=[],
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=NAME,
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon=os.path.join(ROOT, "assets", "icons", "tis.ico"),
    version=os.path.join(ROOT, "packaging", "version_info.txt"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=NAME,
)

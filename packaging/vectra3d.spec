# PyInstaller build file for Vectra3D.
#
# Build with:  uv run pyinstaller packaging/vectra3d.spec --noconfirm --clean
# Zip with:    uv run python -m zipfile -c dist/Vectra3D-0.1.0-windows.zip dist/Vectra3D
# Output:      dist/Vectra3D/Vectra3D.exe  (one folder, shared as the zip),
#              with "Read me first.txt" beside it
#
# Three things here are easy to get wrong and all are deliberate:
#
# 1. MediaPipe ships model and graph files (.tflite, .binarypb) that
#    PyInstaller cannot discover by following imports, so collect_all gathers
#    its data files, native libraries and submodules explicitly.
# 2. The gesture recognizer model is added under "assets/models", the same
#    path it has in the project. That is what lets paths.resource_path() work
#    unchanged whether the app runs from source or from the .exe.
# 3. qdarktheme loads its stylesheet's icons from .svg files inside the
#    package, referenced by URL from the stylesheet rather than imported, so
#    PyInstaller cannot see them either. Without them the themed widgets lose
#    their checkbox ticks and dropdown arrows in the packaged build only,
#    which is the kind of difference that is only noticed after shipping.

import os
import shutil

from PyInstaller.utils.hooks import collect_all

# Shipped next to Vectra3D.exe: SmartScreen, the slow first launch, the
# camera. See the end of this file.
README_NAME = "Read me first.txt"

mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all("mediapipe")
qdarktheme_datas, _, qdarktheme_hiddenimports = collect_all("qdarktheme")

datas = [
    *mediapipe_datas,
    *qdarktheme_datas,
    ("../assets/models/gesture_recognizer.task", "assets/models"),
    # Also given to EXE below: that sets the .exe file's own icon, this lets
    # the running app put the same icon on its window and taskbar button.
    ("../assets/icons/vectra3d.ico", "assets/icons"),
]

a = Analysis(
    ["../src/vectra3d/__main__.py"],
    pathex=["../src"],
    binaries=mediapipe_binaries,
    datas=datas,
    hiddenimports=[*mediapipe_hiddenimports, *qdarktheme_hiddenimports],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Vectra3D",
    icon="../assets/icons/vectra3d.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # No terminal behind the app. `--check-model` still prints its verdict
    # when its output is piped: `.\Vectra3D.exe --check-model | Out-String`
    # in PowerShell, which also waits for it to finish.
    console=False,
    # Left enabled on purpose: a startup failure then shows its traceback in
    # a dialog instead of the window silently never appearing.
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
    upx=False,
    upx_exclude=[],
    name="Vectra3D",
)

# The students' note goes beside the .exe, where they look first - not in
# `datas`, which PyInstaller 6 puts in the `_internal` folder. A spec file is
# plain Python, and COLLECT has built the folder by this line.
shutil.copy(
    os.path.join(SPECPATH, README_NAME),
    os.path.join(DISTPATH, "Vectra3D", README_NAME),
)

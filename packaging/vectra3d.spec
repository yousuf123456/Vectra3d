# PyInstaller build file for Vectra3D.
#
# Build with:  uv run pyinstaller packaging/vectra3d.spec --noconfirm
# Output:      dist/vectra3d/vectra3d.exe  (one folder, shared as a zip)
#
# Two things here are easy to get wrong and both are deliberate:
#
# 1. MediaPipe ships model and graph files (.tflite, .binarypb) that
#    PyInstaller cannot discover by following imports, so collect_all gathers
#    its data files, native libraries and submodules explicitly.
# 2. The gesture recognizer model is added under "assets/models", the same
#    path it has in the project. That is what lets paths.resource_path() work
#    unchanged whether the app runs from source or from the .exe.

from PyInstaller.utils.hooks import collect_all

mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all("mediapipe")

datas = [
    *mediapipe_datas,
    ("../assets/models/gesture_recognizer.task", "assets/models"),
]

a = Analysis(
    ["../src/vectra3d/__main__.py"],
    pathex=["../src"],
    binaries=mediapipe_binaries,
    datas=datas,
    hiddenimports=mediapipe_hiddenimports,
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
    name="vectra3d",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # Kept on until packaging is finished, so a startup failure prints
    # something instead of the window silently never appearing. G6.1 turns
    # this off so students do not see a terminal behind the app.
    console=True,
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
    name="vectra3d",
)

"""Locating files that ship with the app.

Read-only assets (the MediaPipe model, icons) live in the project folder during
development, but PyInstaller unpacks them into a temporary folder at runtime.
`resource_path()` hides that difference, so the rest of the app never needs to
know whether it is running from source or from the packaged .exe.

Every bundled asset must be loaded through this helper. A plain relative path
works from source and then fails only once the app is packaged, which is the
worst moment to find out.
"""

from __future__ import annotations

import sys
from pathlib import Path

# src/vectra3d/paths.py -> src/vectra3d -> src -> project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

# The MediaPipe gesture recognizer model, bundled with the app so that hand
# tracking works offline and nothing is ever downloaded at runtime.
GESTURE_MODEL = "assets/models/gesture_recognizer.task"

# The app's icon, for the window and taskbar. The packaged .exe file carries
# the same icon, set separately in packaging/vectra3d.spec.
APP_ICON = "assets/icons/vectra3d.ico"


def resource_path(relative: str) -> Path:
    """Return the absolute path to a bundled asset.

    `relative` is given relative to the project root, with forward slashes,
    for example "assets/models/gesture_recognizer.task".

    When running from the packaged .exe, PyInstaller sets `sys._MEIPASS` to the
    folder it unpacked the bundled files into, and the asset is resolved there.
    Otherwise the project folder is used.

    The path is returned whether or not the file exists; callers decide how to
    report a missing asset.
    """
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base is not None else _PROJECT_ROOT
    return root.joinpath(*relative.split("/"))

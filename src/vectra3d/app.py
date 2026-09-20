"""Starts the application.

`QT_API` is set before anything imports pyvistaqt. pyvistaqt reaches Qt through
qtpy, which decides at import time which Qt binding to use based on this
variable and on what happens to be installed. Setting it explicitly is what
guarantees PySide6 is used, rather than whichever binding qtpy finds first.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_API", "pyside6")

import sys  # noqa: E402

from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.paths import GESTURE_MODEL, resource_path  # noqa: E402
from vectra3d.ui.main_window import VectraMainWindow  # noqa: E402


def check_model() -> int:
    """Load the bundled hand-tracking model and report whether it worked.

    Run with `--check-model`. This exists so the packaged .exe can prove it
    found and loaded the model, which is the part of packaging most likely to
    break: the model is a data file PyInstaller does not find on its own, and
    inside the .exe it lives in a temporary folder rather than next to the
    project. Printing the resolved path shows which of the two is in use.
    """
    import mediapipe as mp

    model = resource_path(GESTURE_MODEL)
    print(f"model path: {model}")

    if not model.is_file():
        print("FAILED: the model file is not there")
        return 1

    options = mp.tasks.vision.GestureRecognizerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
    )
    with mp.tasks.vision.GestureRecognizer.create_from_options(options):
        print("OK: gesture recognizer created from the bundled model")
    return 0


def main() -> int:
    """Open the main window and run until the user closes it."""
    if "--check-model" in sys.argv[1:]:
        return check_model()

    app = QApplication([])

    window = VectraMainWindow()
    window.show()

    return app.exec()

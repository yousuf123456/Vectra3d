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
from vectra3d.state.store import VectorStore  # noqa: E402
from vectra3d.ui.main_window import VectraMainWindow  # noqa: E402


USAGE = "usage: vectra3d [--check-model]"


def check_model() -> int:
    """Load the bundled hand-tracking model and report whether it worked.

    Run with `--check-model`. This exists so the packaged .exe can prove it
    found and loaded the model, which is the part of packaging most likely to
    break: the model is a data file PyInstaller does not find on its own, and
    inside the .exe it lives in a temporary folder rather than next to the
    project. Printing the resolved path shows which of the two is in use.

    Returns 0 if the model loaded, 1 if it did not.
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
    try:
        with mp.tasks.vision.GestureRecognizer.create_from_options(options):
            print("OK: gesture recognizer created from the bundled model")
    except Exception as exc:
        # A missing file is caught above; this catches a file that is present
        # but unusable - truncated, corrupted, or built for a different
        # version of MediaPipe. The point of this option is to give a clear
        # verdict, so every failure has to end in one rather than a traceback.
        print(f"FAILED: the model file is there but could not be loaded: {exc}")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """Open the main window, or run a command-line option.

    `argv` is the argument list without the program name. It is a parameter so
    that the behaviour can be tested without launching a window.
    """
    args = sys.argv[1:] if argv is None else argv

    if args == ["--check-model"]:
        return check_model()

    if args:
        # Anything unrecognised is reported rather than ignored. A mistyped
        # option used to open the window instead, which is the wrong answer
        # when someone is checking a packaged build and has nothing else to
        # tell them what happened.
        print(f"unrecognised arguments: {' '.join(args)}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 2

    # sys.argv is passed on so that Qt's own options still work, such as
    # -platform offscreen when running without a display.
    app = QApplication(sys.argv)

    # One store for the whole app: the single source of truth every panel and
    # the 3D view read from (`architecture.md` section 2).
    store = VectorStore()

    window = VectraMainWindow(store)
    window.show()

    return app.exec()

"""The loading window shown while the app starts (G6.1b).

The app takes about 25 seconds to load its libraries, and with nothing on
screen a student on a second laptop thought nothing was happening. These
check the loading window can appear before the slow parts load, says what is
loading in order, and gives way to the main window.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d import app as vectra_app  # noqa: E402
from vectra3d.paths import APP_ICON, resource_path  # noqa: E402
from vectra3d.ui.splash import LoadingSplash  # noqa: E402


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_the_app_module_loads_nothing_slow_before_the_splash() -> None:
    # In a fresh interpreter, as a double-click starts one: importing the
    # entry module must not pull in the 3D engine or hand tracking, or the
    # splash could only appear once they had loaded - which is the fault.
    probe = (
        "import sys, vectra3d.app; "
        "print([m for m in ('pyvista', 'vtk', 'pyvistaqt', 'mediapipe', 'cv2') "
        "if m in sys.modules])"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


def test_every_loading_stage_names_a_real_module() -> None:
    for _, module in vectra_app.LOADING_STAGES:
        assert importlib.util.find_spec(module) is not None, module


class RecordingSplash(LoadingSplash):
    def __init__(self, icon: QIcon) -> None:
        super().__init__(icon)
        self.said: list[str] = []

    def say(self, text: str) -> None:
        self.said.append(text)
        super().say(text)


def test_start_says_each_stage_in_order_then_gives_way_to_the_window(
    app: QApplication,
) -> None:
    splash = RecordingSplash(QIcon(str(resource_path(APP_ICON))))
    window = vectra_app.start(splash)
    try:
        assert splash.said == [
            *(text for text, _ in vectra_app.LOADING_STAGES),
            vectra_app.OPENING_TEXT,
        ]
        assert window.isVisible()
        assert not splash.isVisible()
    finally:
        window.close()


def test_the_splash_shows_the_text_it_is_given(app: QApplication) -> None:
    splash = LoadingSplash(QIcon(str(resource_path(APP_ICON))))
    splash.say("Loading hand tracking...")
    assert splash.message() == "Loading hand tracking..."
    splash.close()

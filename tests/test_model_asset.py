"""Proves the bundled MediaPipe model is present and actually usable.

A file-exists check is not enough: a truncated or corrupted download would pass
it and then fail much later, when the camera is first switched on in G4. So
these tests go through `app.check_model()`, the same code the packaged .exe
runs, rather than loading the model a second way. If the loading options ever
change, the test cannot drift away from what the app actually does.

This is an asset test, not a gesture-logic test. The `gestures` layer never
imports MediaPipe (`code-standards.md` section 2); this test is not part of
that layer.
"""

from __future__ import annotations

import pytest

from vectra3d.app import check_model, main
from vectra3d.paths import GESTURE_MODEL, resource_path


def test_model_file_is_bundled() -> None:
    model = resource_path(GESTURE_MODEL)

    assert model.is_file(), f"gesture recognizer model missing at {model}"
    # The float16 bundle is roughly 8 MB; anything tiny means a failed or
    # truncated download, or an error page saved under the model's name.
    assert model.stat().st_size > 1_000_000


def test_model_loads(capsys: pytest.CaptureFixture[str]) -> None:
    assert check_model() == 0

    out = capsys.readouterr().out
    assert "OK:" in out
    # The resolved path is printed so that a packaged run shows whether it
    # used PyInstaller's unpack folder or the project folder.
    assert "gesture_recognizer.task" in out


def test_unrecognised_arguments_are_reported(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # A mistyped option must not fall through to opening the window.
    assert main(["--check-modl"]) == 2

    assert "unrecognised arguments" in capsys.readouterr().err


def test_check_model_option_is_accepted(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--check-model"]) == 0

    assert "OK:" in capsys.readouterr().out

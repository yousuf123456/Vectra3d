"""Tests for `resource_path()`, the only way the app locates bundled assets."""

from __future__ import annotations

import sys
from pathlib import Path

from vectra3d.paths import resource_path


def test_resolves_a_file_in_the_project_folder() -> None:
    path = resource_path("pyproject.toml")

    assert path.is_absolute()
    assert path.is_file()


def test_nested_relative_path_uses_forward_slashes() -> None:
    path = resource_path("assets/models/gesture_recognizer.task")

    assert path.parent.name == "models"
    assert path.name == "gesture_recognizer.task"


def test_missing_file_still_returns_a_path() -> None:
    # Callers decide how to report a missing asset, so no exception here.
    path = resource_path("assets/does-not-exist.task")

    assert path.is_absolute()
    assert not path.exists()


def test_uses_pyinstaller_unpack_folder_when_frozen(
    tmp_path: Path, monkeypatch: object
) -> None:
    # PyInstaller sets sys._MEIPASS to the folder it unpacked the app into.
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)  # type: ignore[attr-defined]

    path = resource_path("assets/models/gesture_recognizer.task")

    assert path == tmp_path / "assets" / "models" / "gesture_recognizer.task"

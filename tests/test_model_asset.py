"""Proves the bundled MediaPipe model is present and actually usable.

A file-exists check is not enough: a truncated or corrupted download would pass
it and then fail much later, when the camera is first switched on in G4. So
this test builds a real GestureRecognizer from the file, which is the same call
the tracker will make.

This is an asset test, not a gesture-logic test. The `gestures` layer never
imports MediaPipe (`code-standards.md` section 2); this test is not part of
that layer.
"""

from __future__ import annotations

import mediapipe as mp

from vectra3d.paths import GESTURE_MODEL, resource_path

BaseOptions = mp.tasks.BaseOptions
GestureRecognizer = mp.tasks.vision.GestureRecognizer
GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
VisionRunningMode = mp.tasks.vision.RunningMode


def test_model_file_is_bundled() -> None:
    model = resource_path(GESTURE_MODEL)

    assert model.is_file(), f"gesture recognizer model missing at {model}"
    # The float16 bundle is roughly 8 MB; anything tiny means a failed or
    # truncated download, or an error page saved under the model's name.
    assert model.stat().st_size > 1_000_000


def test_model_loads_in_video_mode() -> None:
    # VIDEO mode is what the tracker thread uses (`architecture.md` 4.3), so
    # the test exercises the configuration the app actually runs.
    options = GestureRecognizerOptions(
        base_options=BaseOptions(model_asset_path=str(resource_path(GESTURE_MODEL))),
        running_mode=VisionRunningMode.VIDEO,
    )

    with GestureRecognizer.create_from_options(options) as recognizer:
        assert recognizer is not None

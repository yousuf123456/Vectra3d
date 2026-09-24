"""The camera preview: what it says about the hands, and what it draws."""

from __future__ import annotations

import numpy as np
import pytest

from vectra3d.gestures.hand_frame import NO_GESTURE, Hand, HandFrame

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.ui import theme  # noqa: E402
from vectra3d.ui.camera_preview import (  # noqa: E402
    CAMERA_LOST_TEXT,
    GESTURE_NAMES,
    NO_CAMERA_TEXT,
    NO_HAND_TEXT,
    PICTURE_HEIGHT,
    PICTURE_WIDTH,
    CameraPreview,
    gesture_text,
    status_text,
)

# Every label in the bundled model's `labels.txt`.
MODEL_LABELS = (
    "None",
    "Closed_Fist",
    "Open_Palm",
    "Pointing_Up",
    "Thumb_Down",
    "Thumb_Up",
    "Victory",
    "ILoveYou",
)


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def hand_at(x: float, y: float, gesture: str = NO_GESTURE) -> Hand:
    return Hand(landmarks=((x, y),) * 21, gesture=gesture, gesture_score=0.9)


# --- Words ---


def test_every_model_label_has_a_plain_name() -> None:
    assert set(GESTURE_NAMES) == set(MODEL_LABELS)
    for label in MODEL_LABELS:
        assert "_" not in gesture_text(label)


def test_no_gesture_and_a_named_one() -> None:
    assert gesture_text(NO_GESTURE) == "No gesture"
    assert gesture_text("Thumb_Up") == "Thumb up"
    assert gesture_text("ILoveYou") == "I love you"


def test_an_unknown_label_is_shown_as_is() -> None:
    assert gesture_text("Wave") == "Wave"


def test_no_hands() -> None:
    assert status_text(HandFrame(hands=(), timestamp_ms=0)) == NO_HAND_TEXT


def test_one_hand_is_just_its_gesture() -> None:
    frame = HandFrame(hands=(hand_at(0.5, 0.5, "Victory"),), timestamp_ms=0)

    assert status_text(frame) == "Victory"


def test_two_hands_are_named_by_side_whatever_order_they_arrive_in() -> None:
    left = hand_at(0.2, 0.5, "Thumb_Up")
    right = hand_at(0.8, 0.5, "Open_Palm")
    expected = "Left: Thumb up\nRight: Open palm"

    assert status_text(HandFrame(hands=(left, right), timestamp_ms=0)) == expected
    assert status_text(HandFrame(hands=(right, left), timestamp_ms=0)) == expected


# --- The widget ---


def test_messages_replace_the_status(app: QApplication) -> None:
    preview = CameraPreview()

    preview.show_no_camera()
    assert preview.status == NO_CAMERA_TEXT

    preview.show_camera_lost()
    assert preview.status == CAMERA_LOST_TEXT


def test_a_frame_with_no_hands_says_so(app: QApplication) -> None:
    preview = CameraPreview()
    pixels = np.zeros((480, 640, 3), dtype=np.uint8)

    preview.show_frame(pixels, HandFrame(hands=(), timestamp_ms=0))

    assert preview.status == NO_HAND_TEXT


def picture_of(preview: CameraPreview):
    return preview.layout().itemAt(0).widget().grab().toImage()


def test_the_picture_and_the_hand_are_drawn(app: QApplication) -> None:
    preview = CameraPreview()
    # A solid red picture, and a hand whose every point is a quarter of the
    # way across and down, so the point colour lands on one known spot.
    pixels = np.zeros((480, 640, 3), dtype=np.uint8)
    pixels[:, :, 0] = 255
    preview.show_frame(pixels, HandFrame(hands=(hand_at(0.25, 0.25),), timestamp_ms=0))

    image = picture_of(preview)

    assert image.pixelColor(PICTURE_WIDTH * 3 // 4, PICTURE_HEIGHT * 3 // 4) == QColor(
        255, 0, 0
    )
    assert image.pixelColor(PICTURE_WIDTH // 4, PICTURE_HEIGHT // 4) == QColor(
        theme.HAND_POINT
    )


def test_a_message_clears_the_last_picture(app: QApplication) -> None:
    # A frozen frame would look like a camera that is still working.
    preview = CameraPreview()
    pixels = np.full((480, 640, 3), 255, dtype=np.uint8)
    preview.show_frame(pixels, HandFrame(hands=(), timestamp_ms=0))

    preview.show_camera_lost()

    centre = picture_of(preview).pixelColor(PICTURE_WIDTH // 2, PICTURE_HEIGHT // 2)
    assert centre == QColor(theme.PREVIEW_BACKGROUND)

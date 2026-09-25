"""The camera preview: what it says about the hands, and what it draws."""

from __future__ import annotations

import numpy as np
import pytest

from vectra3d import config
from vectra3d.gestures.hand_frame import NO_GESTURE, Hand, HandFrame
from vectra3d.gestures.hand_metrics import TrackedHand
from vectra3d.gestures.intents import Cancel, Commit, HoldTriggered
from vectra3d.gestures.state_machine import GestureState, HoldStatus, MachineOutput

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.state import actions  # noqa: E402
from vectra3d.state.store import VectorStore  # noqa: E402
from vectra3d.ui import theme  # noqa: E402
from vectra3d.ui.camera_preview import (  # noqa: E402
    CAMERA_LOST_TEXT,
    CANCELLED_TEXT,
    COMMITTED_TEXT,
    GESTURE_NAMES,
    NO_CAMERA_TEXT,
    NO_HAND_TEXT,
    PICTURE_HEIGHT,
    PICTURE_WIDTH,
    PINCHING_TEXT,
    CameraPreview,
    gesture_text,
    machine_text,
    outcome_text,
    status_text,
)
from vectra3d.ui.gesture_controller import Joystick  # noqa: E402
from vectra3d.ui.main_window import VectraMainWindow  # noqa: E402

ASPECT = 4 / 3
IDLE = MachineOutput(GestureState.IDLE, (), None)

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


def tracked(
    wrist_x: float, gesture: str = NO_GESTURE, pinching: bool = False
) -> TrackedHand:
    return TrackedHand(
        hand_id=0,
        gesture=gesture,
        gesture_score=0.9,
        wrist=(wrist_x, 0.5),
        scale=0.2,
        pinch_distance_hs=0.1 if pinching else 1.0,
        pinching=pinching,
        pinch_point=(wrist_x, 0.4),
    )


def empty_frame() -> HandFrame:
    return HandFrame(hands=(), timestamp_ms=0, aspect=ASPECT)


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
    assert status_text(()) == NO_HAND_TEXT


def test_one_hand_is_just_its_gesture() -> None:
    assert status_text((tracked(0.5, "Victory"),)) == "Victory"


def test_two_hands_are_named_by_side_whatever_order_they_arrive_in() -> None:
    left = tracked(0.2, "Thumb_Up")
    right = tracked(0.8, "Open_Palm")
    expected = "Left: Thumb up\nRight: Open palm"

    assert status_text((left, right)) == expected
    assert status_text((right, left)) == expected


def test_a_pinch_with_no_gesture_just_says_pinching() -> None:
    assert status_text((tracked(0.5, pinching=True),)) == PINCHING_TEXT


def test_a_pinch_and_a_gesture_are_both_named() -> None:
    assert status_text((tracked(0.5, "Victory", pinching=True),)) == (
        "Victory, pinching"
    )


def test_each_of_two_hands_shows_its_own_pinch() -> None:
    left = tracked(0.2, pinching=True)
    right = tracked(0.8, "Open_Palm")

    assert status_text((right, left)) == "Left: Pinching\nRight: Open palm"


def test_the_gesture_line_names_what_is_happening() -> None:
    steering = MachineOutput(GestureState.STEERING, (), None)
    waiting = MachineOutput(GestureState.WAITING, (), None)

    assert machine_text(steering, "") == "Steering"
    assert machine_text(waiting, "") == "Waiting for a second hand"


def test_a_hold_shows_its_progress() -> None:
    holding = MachineOutput(GestureState.HOLDING, (), HoldStatus("Thumb_Up", 0.6))

    assert machine_text(holding, "") == "Holding Thumb up: 60%"


def test_idle_says_how_the_last_gesture_ended() -> None:
    assert machine_text(IDLE, "") == ""
    assert machine_text(IDLE, CANCELLED_TEXT) == CANCELLED_TEXT


def test_each_way_a_gesture_ends_has_its_own_words() -> None:
    def ended(intent) -> MachineOutput:
        return MachineOutput(GestureState.IDLE, (intent,), None)

    assert outcome_text(ended(Commit())) == COMMITTED_TEXT
    assert outcome_text(ended(Cancel())) == CANCELLED_TEXT
    assert outcome_text(ended(HoldTriggered("Victory"))) == (
        "Last gesture: Victory held"
    )
    assert outcome_text(IDLE) is None


def test_the_last_outcome_stays_until_the_next_gesture(app: QApplication) -> None:
    preview = CameraPreview()
    pixels = np.zeros((480, 640, 3), dtype=np.uint8)
    cancelled = MachineOutput(GestureState.IDLE, (Cancel(),), None)

    preview.show_frame(pixels, empty_frame(), (), cancelled)
    preview.show_frame(pixels, empty_frame(), (), IDLE)

    assert preview.status == f"{NO_HAND_TEXT}\n{CANCELLED_TEXT}"


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

    preview.show_frame(pixels, empty_frame(), (), IDLE)

    assert preview.status == NO_HAND_TEXT


def picture_of(preview: CameraPreview):
    return preview.layout().itemAt(0).widget().grab().toImage()


def test_the_picture_and_the_hand_are_drawn(app: QApplication) -> None:
    preview = CameraPreview()
    # A solid red picture, and a hand whose every point is a quarter of the
    # way across and down, so the point colour lands on one known spot.
    pixels = np.zeros((480, 640, 3), dtype=np.uint8)
    pixels[:, :, 0] = 255
    hand = hand_at(0.25, 0.25)
    frame = HandFrame(hands=(hand,), timestamp_ms=0, aspect=ASPECT)
    preview.show_frame(pixels, frame, (tracked(0.25),), IDLE)

    image = picture_of(preview)

    assert image.pixelColor(PICTURE_WIDTH * 3 // 4, PICTURE_HEIGHT * 3 // 4) == QColor(
        255, 0, 0
    )
    assert image.pixelColor(PICTURE_WIDTH // 4, PICTURE_HEIGHT // 4) == QColor(
        theme.HAND_POINT
    )


def test_the_steering_joystick_is_drawn_over_the_picture(app: QApplication) -> None:
    # A black picture filling the 240x180 area, so one picture height is 180
    # pixels. Anchor at the centre: (2/3, 1/2) in picture heights is pixel
    # (120, 90). The pinch point 0.25 picture heights to the right is 45 px.
    preview = CameraPreview()
    pixels = np.zeros((480, 640, 3), dtype=np.uint8)
    frame = HandFrame(hands=(), timestamp_ms=0, aspect=ASPECT)
    centre = (ASPECT / 2, 0.5)
    joystick = Joystick(centre, (centre[0] + 0.25, 0.5), 0.25)

    preview.show_frame(pixels, frame, (), IDLE, None, joystick)
    image = picture_of(preview)

    def is_joystick(x: int, y: int) -> bool:
        # Anti-aliased edges blend with the black, so near enough is enough.
        colour = image.pixelColor(x, y)
        wanted = QColor(theme.JOYSTICK)
        return (
            abs(colour.red() - wanted.red()) < 60
            and abs(colour.green() - wanted.green()) < 60
            and abs(colour.blue() - wanted.blue()) < 60
        )

    # The anchor, and the line on its way to the pinch point.
    assert is_joystick(120, 90)
    assert is_joystick(150, 90)
    # The dead-zone ring: 0.3 hs * 0.25 * 180 = 13.5 px above the anchor.
    assert any(is_joystick(120, y) for y in (75, 76, 77))
    # Nothing is drawn well outside it, and nothing at all without a joystick.
    assert not is_joystick(120, 50)
    preview.show_frame(pixels, frame, (), IDLE)
    image = picture_of(preview)
    assert not is_joystick(120, 90)


def test_a_message_clears_the_last_picture(app: QApplication) -> None:
    # A frozen frame would look like a camera that is still working.
    preview = CameraPreview()
    pixels = np.full((480, 640, 3), 255, dtype=np.uint8)
    preview.show_frame(pixels, empty_frame(), (), IDLE)

    preview.show_camera_lost()

    centre = picture_of(preview).pixelColor(PICTURE_WIDTH // 2, PICTURE_HEIGHT // 2)
    assert centre == QColor(theme.PREVIEW_BACKGROUND)


# --- Through the window ---


def pinching_hand() -> Hand:
    """A hand held with the thumb and index tips 0.1 hs apart.

    Wrist at (0.5, 0.8), middle-finger base 0.2 straight above it: 1 hs is
    0.2 picture heights whatever the aspect, because the two differ only in y.
    The fingertips are 0.02 apart in y, which is 0.1 hs - under the 0.25 hs a
    pinch needs to start.
    """
    points = [(0.5, 0.5)] * 21
    points[0] = (0.5, 0.8)
    points[9] = (0.5, 0.6)
    points[4] = (0.5, 0.40)
    points[8] = (0.5, 0.42)
    return Hand(landmarks=tuple(points), gesture=NO_GESTURE, gesture_score=0.9)


def test_the_window_measures_each_frame_and_the_preview_says_pinching(
    app: QApplication,
) -> None:
    # The window's own slot, called directly so that anything it raises
    # reaches the test instead of being swallowed by Qt. That the tracker is
    # connected to this slot is proven across threads in the tracker's tests.
    # A vector to steer: from G5.5 a steer with nothing to act on is refused,
    # and the camera strip says so instead of "Steering".
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    window = VectraMainWindow(store)
    pixels = np.zeros((480, 640, 3), dtype=np.uint8)
    try:
        frame = HandFrame(hands=(pinching_hand(),), timestamp_ms=0, aspect=ASPECT)
        window._on_hand_frame(pixels, frame)
        assert window.camera_preview.status == (
            f"{PINCHING_TEXT}\nWaiting for a second hand"
        )

        # Held past the two-hand window: the state machine ran too.
        past_window_ms = round(config.TWO_HAND_PINCH_WINDOW_S * 1000) + 100
        later = HandFrame(
            hands=(pinching_hand(),), timestamp_ms=past_window_ms, aspect=ASPECT
        )
        window._on_hand_frame(pixels, later)
        assert window.camera_preview.status == f"{PINCHING_TEXT}\nSteering"
    finally:
        window.close()

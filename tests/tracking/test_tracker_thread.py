"""The tracker thread, and the plain data it turns MediaPipe's results into.

No webcam is needed. The thread is handed a fake camera that produces black
pictures, which the real recognizer runs on and finds no hands in. That
proves the loop, the signals and the clean stop; whether real hands are
recognized is checked by hand (see the step report).
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.gestures.hand_frame import NO_GESTURE, HandFrame  # noqa: E402
from vectra3d.tracking.camera import open_camera  # noqa: E402
from vectra3d.tracking.tracker_thread import (  # noqa: E402
    TrackerThread,
    next_timestamp_ms,
    to_hand_frame,
)
from vectra3d.state.store import VectorStore  # noqa: E402
from vectra3d.ui.camera_preview import NO_HAND_TEXT, STARTING_TEXT  # noqa: E402
from vectra3d.ui.main_window import VectraMainWindow  # noqa: E402

WAIT_S = 10.0


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


class FakeCamera:
    """Delivers `frames` black pictures, then fails as an unplugged camera does."""

    def __init__(self, frames: int | None = None) -> None:
        self.remaining = frames
        self.released = False

    def read(self) -> tuple[bool, np.ndarray | None]:
        if self.remaining is not None:
            if self.remaining == 0:
                return False, None
            self.remaining -= 1
        time.sleep(0.01)
        return True, np.zeros((480, 640, 3), dtype=np.uint8)

    def release(self) -> None:
        self.released = True


def point(x: float, y: float) -> SimpleNamespace:
    return SimpleNamespace(x=x, y=y, z=0.5)


def category(name: str, score: float) -> SimpleNamespace:
    return SimpleNamespace(category_name=name, score=score)


def wait_until(condition, app: QApplication) -> None:
    deadline = time.monotonic() + WAIT_S
    while not condition():
        assert time.monotonic() < deadline, "timed out waiting for the tracker"
        app.processEvents()
        time.sleep(0.01)


# --- MediaPipe's result as plain data ---


def test_no_hands_gives_an_empty_frame() -> None:
    result = SimpleNamespace(hand_landmarks=[], gestures=[])

    assert to_hand_frame(result, 1234, 4 / 3) == HandFrame(
        hands=(), timestamp_ms=1234, aspect=4 / 3
    )


def test_two_hands_keep_their_points_and_gestures_in_order() -> None:
    first = [point(0.1 * i / 20, 0.2) for i in range(21)]
    second = [point(0.9, 0.05 * i / 20) for i in range(21)]
    result = SimpleNamespace(
        hand_landmarks=[first, second],
        gestures=[[category("Thumb_Up", 0.9)], [category("Victory", 0.7)]],
    )

    frame = to_hand_frame(result, 5, 4 / 3)

    assert len(frame.hands) == 2
    assert frame.hands[0].gesture == "Thumb_Up"
    assert frame.hands[0].gesture_score == 0.9
    assert frame.hands[1].gesture == "Victory"
    assert len(frame.hands[0].landmarks) == 21
    # Depth is dropped: each point is (x, y) only.
    assert frame.hands[0].landmarks[20] == (0.1, 0.2)
    assert frame.hands[1].landmarks[0] == (0.9, 0.0)


def test_a_hand_with_no_gesture_is_kept_as_no_gesture() -> None:
    result = SimpleNamespace(hand_landmarks=[[point(0.5, 0.5)] * 21], gestures=[[]])

    hand = to_hand_frame(result, 0, 4 / 3).hands[0]

    assert hand.gesture == NO_GESTURE
    assert hand.gesture_score == 0.0


# --- Timestamps ---


def test_timestamps_always_increase() -> None:
    first = next_timestamp_ms(None)
    # A previous stamp ahead of the clock, or equal to it, is still beaten.
    assert next_timestamp_ms(first + 1000) == first + 1001
    assert next_timestamp_ms(first) > first


def test_timestamps_increase_across_a_fast_run() -> None:
    stamps = [next_timestamp_ms(None)]
    for _ in range(1000):
        stamps.append(next_timestamp_ms(stamps[-1]))

    assert all(later > earlier for earlier, later in zip(stamps, stamps[1:]))


# --- The camera ---


def test_a_missing_camera_opens_as_none() -> None:
    # No machine this runs on has ten cameras.
    assert open_camera(9) is None


# --- The thread ---


def test_no_camera_is_reported_and_the_thread_ends(app: QApplication) -> None:
    tracker = TrackerThread(camera_opener=lambda: None)
    reported = []
    tracker.camera_unavailable.connect(
        lambda: reported.append(True), Qt.ConnectionType.DirectConnection
    )

    tracker.start()

    assert tracker.wait(int(WAIT_S * 1000))
    assert reported == [True]


def test_frames_arrive_and_stop_releases_the_camera(app: QApplication) -> None:
    camera = FakeCamera()
    tracker = TrackerThread(camera_opener=lambda: camera)
    frames = []
    tracker.frame_ready.connect(
        lambda pixels, frame: frames.append((pixels, frame)),
        Qt.ConnectionType.DirectConnection,
    )

    tracker.start()
    wait_until(lambda: len(frames) >= 3, app)
    tracker.stop()

    assert tracker.isFinished()
    assert camera.released
    pixels, frame = frames[0]
    # Converted, not the camera's own array: RGB, same size.
    assert pixels.shape == (480, 640, 3)
    # The shape is read from the picture, not assumed.
    assert frame.aspect == 640 / 480
    assert frame.hands == ()
    stamps = [frame.timestamp_ms for _, frame in frames]
    assert all(later > earlier for earlier, later in zip(stamps, stamps[1:]))


def test_a_camera_that_stops_is_reported_and_released(app: QApplication) -> None:
    camera = FakeCamera(frames=2)
    tracker = TrackerThread(camera_opener=lambda: camera)
    lost = []
    tracker.camera_lost.connect(
        lambda: lost.append(True), Qt.ConnectionType.DirectConnection
    )

    tracker.start()

    assert tracker.wait(int(WAIT_S * 1000))
    assert lost == [True]
    assert camera.released


def test_pictures_reach_the_preview_through_the_window_across_threads(
    app: QApplication,
) -> None:
    # The connection the window makes: default, so Qt queues it from the
    # tracker's thread to the window's, where the hands are measured and the
    # preview updated. A slot that failed here would be swallowed by Qt,
    # which is why this goes through the real window and not a stand-in.
    window = VectraMainWindow(VectorStore())
    tracker = TrackerThread(camera_opener=lambda: FakeCamera())
    tracker.frame_ready.connect(window._on_hand_frame)
    assert window.camera_preview.status == STARTING_TEXT

    tracker.start()
    try:
        wait_until(lambda: window.camera_preview.status == NO_HAND_TEXT, app)
    finally:
        tracker.stop()
        window.close()

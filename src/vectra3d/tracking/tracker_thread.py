"""The background thread that watches the camera.

Each pass of the loop reads one frame, mirrors it, converts it to RGB, runs
MediaPipe's gesture recognizer on it, and sends the picture and a plain
`HandFrame` to the main thread as a Qt signal (`architecture.md` section 4.2).

Rules this module keeps:
- **It never touches a widget, PyVista, or the store.** VTK and Qt widgets are
  not thread-safe. It only emits signals carrying plain data, which Qt queues
  across to the main thread.
- **Frames are dropped, not queued.** Read, recognize, send, in that order, so
  the camera can never get ahead of the tracker: a frame that arrives while
  one is being recognized is simply never read. Measured on the target laptop,
  recognition takes about 16 ms against the camera's 33 ms between frames.
- **Nothing is saved.** A frame lives only as long as the preview shows it.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

import cv2
import mediapipe as mp
from PySide6.QtCore import QThread, Signal

from vectra3d.gestures.hand_frame import NO_GESTURE, Hand, HandFrame
from vectra3d.paths import GESTURE_MODEL, resource_path
from vectra3d.tracking.camera import open_camera

# `interaction-spec.md` section 1: up to two hands. MediaPipe's own default
# is one, which would make every two-hand gesture in G5 impossible.
MAX_HANDS = 2


def create_recognizer() -> mp.tasks.vision.GestureRecognizer:
    """Build the gesture recognizer from the bundled model.

    The one place the recognizer's options are set. `app.check_model()` uses
    it too, so the packaged app's self-check proves the exact setup the
    camera runs with rather than a copy of it.
    """
    options = mp.tasks.vision.GestureRecognizerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=str(resource_path(GESTURE_MODEL))
        ),
        # VIDEO mode is called synchronously with increasing timestamps,
        # which suits a loop that already runs on its own thread
        # (`architecture.md` section 4.3).
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=MAX_HANDS,
    )
    return mp.tasks.vision.GestureRecognizer.create_from_options(options)


def next_timestamp_ms(previous: int | None) -> int:
    """The timestamp for the next frame, in milliseconds.

    VIDEO mode rejects a timestamp that does not increase. A monotonic clock
    never goes backwards, but two frames can land in the same millisecond,
    so the value is pushed forward by one when that happens.
    """
    now = time.monotonic_ns() // 1_000_000
    if previous is not None and now <= previous:
        return previous + 1
    return now


def to_hand_frame(result: Any, timestamp_ms: int, aspect: float) -> HandFrame:
    """Turn a MediaPipe `GestureRecognizerResult` into a plain `HandFrame`.

    `result.hand_landmarks[i]` and `result.gestures[i]` describe the same
    hand. A hand whose gesture list comes back empty is treated as making no
    gesture, rather than being dropped: it is still a hand on screen.
    `aspect` is the recognized picture's width over its height.
    """
    hands = []
    for index, points in enumerate(result.hand_landmarks):
        categories = result.gestures[index] if index < len(result.gestures) else []
        top = categories[0] if categories else None
        hands.append(
            Hand(
                landmarks=tuple((point.x, point.y) for point in points),
                gesture=top.category_name if top is not None else NO_GESTURE,
                gesture_score=top.score if top is not None else 0.0,
            )
        )
    return HandFrame(hands=tuple(hands), timestamp_ms=timestamp_ms, aspect=aspect)


class TrackerThread(QThread):
    """Reads the camera and recognizes hands until asked to stop.

    `run()` is overridden rather than moving a worker object onto a thread.
    The work is one blocking loop, which is what `run()` is for; a worker
    object relies on the thread's event loop, which a blocking loop would
    never let run.
    """

    # The mirrored RGB picture (a NumPy array) and the hands found in it.
    frame_ready = Signal(object, object)
    # No camera could be opened. The thread ends.
    camera_unavailable = Signal()
    # The camera was working and stopped sending pictures. The thread ends.
    camera_lost = Signal()

    def __init__(
        self,
        camera_opener: Callable[[], Any] = open_camera,
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        # A parameter so tests can hand the thread a fake camera.
        self._open_camera = camera_opener

    def stop(self) -> None:
        """Ask the loop to finish and wait until it has let go of the camera."""
        self.requestInterruption()
        self.wait()

    def run(self) -> None:
        # The camera is tried before the model is loaded, so a laptop with no
        # camera finds out at once instead of after the model loads.
        camera = self._open_camera()
        if camera is None:
            self.camera_unavailable.emit()
            return

        try:
            with create_recognizer() as recognizer:
                timestamp = None
                while not self.isInterruptionRequested():
                    ok, frame = camera.read()
                    if not ok:
                        self.camera_lost.emit()
                        return
                    # Mirrored before recognition, so the landmarks line up
                    # with the mirrored picture the student sees.
                    rgb = cv2.cvtColor(cv2.flip(frame, 1), cv2.COLOR_BGR2RGB)
                    timestamp = next_timestamp_ms(timestamp)
                    result = recognizer.recognize_for_video(
                        mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb),
                        timestamp,
                    )
                    # Read from the picture itself: the camera, not the app,
                    # decides its resolution.
                    height, width = rgb.shape[:2]
                    self.frame_ready.emit(
                        rgb, to_hand_frame(result, timestamp, width / height)
                    )
        finally:
            camera.release()

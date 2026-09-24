"""What the tracker sees in one camera frame, as plain data.

This is the boundary between hand tracking and everything after it. The
tracker thread turns each MediaPipe result into a `HandFrame` and sends that,
so nothing downstream - the preview now, the gesture state machine from G5 -
ever holds a MediaPipe object. It is also what lets G5 test gestures with
synthetic hands: a `HandFrame` can be written out by hand in a test.

Two things MediaPipe reports are deliberately left out:
- **Depth (z).** `project-overview.md` rules out gestures that rely on moving
  the hand toward or away from the camera, because one webcam cannot judge
  depth reliably.
- **Handedness (left / right).** `interaction-spec.md` section 1 lets either
  hand do every gesture, and `library-docs.md` records that the app does not
  use the labels.
"""

from __future__ import annotations

from dataclasses import dataclass

# MediaPipe's label for a hand that is visible but not making any of its
# built-in gestures. Taken from the label file inside the bundled model.
NO_GESTURE = "None"


@dataclass(frozen=True)
class Hand:
    """One detected hand.

    `landmarks` holds MediaPipe's 21 hand points in its own order, each as
    (x, y) normalised to 0-1 across the *mirrored* image: x grows to the
    right, y grows downwards.
    """

    landmarks: tuple[tuple[float, float], ...]
    gesture: str
    gesture_score: float


@dataclass(frozen=True)
class HandFrame:
    """Every hand found in one frame, and when the frame was taken.

    `timestamp_ms` is the same increasing millisecond clock the recognizer
    was given, so G5's timeouts can be measured in frames' own time.

    `aspect` is the picture's width divided by its height. Landmarks are 0-1
    across each side separately, so on a 640x480 picture one unit of x is a
    third longer than one unit of y; any distance measured between landmarks
    has to multiply x by this first. There is no default, because a guessed
    4:3 would quietly mis-measure on a camera of any other shape.
    """

    hands: tuple[Hand, ...]
    timestamp_ms: int
    aspect: float

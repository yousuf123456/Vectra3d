"""The camera preview strip under the 3D view (F-02).

Shows the mirrored webcam picture with every detected hand drawn on it, and
beside it the name of the gesture each hand is making and whether it is
pinching - or a plain message when there is no camera. It only displays what the tracker thread sends; it
changes nothing.

The hands are drawn with `QPainter` over the picture, because MediaPipe's own
drawing helpers went with `mp.solutions`. G5 draws its steering joystick and
hold progress ring the same way, on top of this.

Only the latest picture is kept. If several arrive before the window next
repaints, Qt merges the repaint requests and the earlier pictures are never
drawn at all - frames are dropped, never queued. None is saved.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from vectra3d.gestures.hand_frame import NO_GESTURE, HandFrame
from vectra3d.gestures.hand_metrics import TrackedHand
from vectra3d.ui import theme

# 4:3, the shape of the picture a laptop webcam delivers (640x480), so the
# picture fills the area without bars.
PICTURE_WIDTH = 240
PICTURE_HEIGHT = 180

NO_HAND_TEXT = "No hand detected"
PINCHING_TEXT = "Pinching"
STARTING_TEXT = "Starting the camera..."
NO_CAMERA_TEXT = "No webcam found. Everything still works from the panels."
CAMERA_LOST_TEXT = (
    "The webcam stopped sending pictures. Everything still works from the panels."
)

# MediaPipe's gesture labels as a student would say them. Written out rather
# than derived from the labels, because "ILoveYou" and "None" do not turn into
# sensible text by splitting on underscores.
GESTURE_NAMES = {
    NO_GESTURE: "No gesture",
    "Closed_Fist": "Closed fist",
    "Open_Palm": "Open palm",
    "Pointing_Up": "Pointing up",
    "Thumb_Down": "Thumb down",
    "Thumb_Up": "Thumb up",
    "Victory": "Victory",
    "ILoveYou": "I love you",
}

# Which of MediaPipe's 21 hand points are joined by a line: the palm outline,
# then each finger from its base to its tip. MediaPipe used to provide this as
# `mp.solutions.hands.HAND_CONNECTIONS`, which went with `mp.solutions`.
HAND_CONNECTIONS = (
    (0, 1), (0, 5), (0, 17), (5, 9), (9, 13), (13, 17),  # palm
    (1, 2), (2, 3), (3, 4),  # thumb
    (5, 6), (6, 7), (7, 8),  # index
    (9, 10), (10, 11), (11, 12),  # middle
    (13, 14), (14, 15), (15, 16),  # ring
    (17, 18), (18, 19), (19, 20),  # little finger
)  # fmt: skip

LINE_WIDTH = 1.5
POINT_RADIUS = 2.5


def gesture_text(label: str) -> str:
    """A gesture label in plain words. An unrecognised label is shown as is."""
    return GESTURE_NAMES.get(label, label)


def hand_text(hand: TrackedHand) -> str:
    """One hand's gesture in plain words, and whether it is pinching.

    A pinch is not one of MediaPipe's gestures - it is measured from the
    fingertips - so a hand can be both. When it is only pinching, "No gesture,
    pinching" would bury the one thing it is doing, so it just says so.
    """
    if not hand.pinching:
        return gesture_text(hand.gesture)
    if hand.gesture == NO_GESTURE:
        return PINCHING_TEXT
    return f"{gesture_text(hand.gesture)}, pinching"


def status_text(hands: tuple[TrackedHand, ...]) -> str:
    """What the strip says about the hands in one frame.

    With two hands, each is named by the side of the picture it is on, so the
    student can tell which line is which. MediaPipe lists hands in no stable
    order, so they are sorted by where the wrist is.
    """
    if not hands:
        return NO_HAND_TEXT
    if len(hands) == 1:
        return hand_text(hands[0])
    left, right = sorted(hands, key=lambda hand: hand.wrist[0])
    return f"Left: {hand_text(left)}\nRight: {hand_text(right)}"


class _Picture(QWidget):
    """The picture with the hands drawn over it."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(PICTURE_WIDTH, PICTURE_HEIGHT)
        self._pixels: np.ndarray | None = None
        self._frame: HandFrame | None = None

    def show_frame(self, pixels: np.ndarray | None, frame: HandFrame | None) -> None:
        self._pixels = pixels
        self._frame = frame
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(theme.PREVIEW_BACKGROUND))
        if self._pixels is None:
            return

        height, width = self._pixels.shape[:2]
        # The QImage reads the array's memory directly; `self._pixels` keeps
        # that memory alive for as long as the image is drawn.
        image = QImage(
            self._pixels.data,
            width,
            height,
            self._pixels.strides[0],
            QImage.Format.Format_RGB888,
        )
        target = _fit(width, height, self.width(), self.height())
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(target, image)

        if self._frame is not None:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            for hand in self._frame.hands:
                _draw_hand(painter, hand.landmarks, target)


def _fit(width: int, height: int, area_width: int, area_height: int) -> QRectF:
    """The largest rectangle of the picture's shape that fits, centred."""
    scale = min(area_width / width, area_height / height)
    drawn_width, drawn_height = width * scale, height * scale
    return QRectF(
        (area_width - drawn_width) / 2,
        (area_height - drawn_height) / 2,
        drawn_width,
        drawn_height,
    )


def _draw_hand(
    painter: QPainter,
    landmarks: tuple[tuple[float, float], ...],
    target: QRectF,
) -> None:
    # Landmarks are 0-1 across the picture, so they scale with it.
    points = [
        QPointF(target.x() + x * target.width(), target.y() + y * target.height())
        for x, y in landmarks
    ]
    painter.setPen(QPen(QColor(theme.HAND_LINE), LINE_WIDTH))
    for start, end in HAND_CONNECTIONS:
        painter.drawLine(points[start], points[end])
    painter.setBrush(QColor(theme.HAND_POINT))
    for point in points:
        painter.drawEllipse(point, POINT_RADIUS, POINT_RADIUS)


class CameraPreview(QWidget):
    """The picture on the left, what the hands are doing on the right."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._picture = _Picture(self)
        self._status = QLabel(STARTING_TEXT, self)
        self._status.setWordWrap(True)
        self._status.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(theme.GAP, theme.GAP, theme.GAP, theme.GAP)
        layout.setSpacing(theme.GAP_LARGE)
        layout.addWidget(self._picture)
        layout.addWidget(self._status, 1)

    @property
    def status(self) -> str:
        return self._status.text()

    def show_frame(
        self, pixels: np.ndarray, frame: HandFrame, hands: tuple[TrackedHand, ...]
    ) -> None:
        """Show one picture, the raw hands drawn on it, and what they are doing.

        `hands` are the same hands as `frame.hands`, measured. The raw points
        are drawn, not the smoothed ones, so the picture shows exactly what
        the tracker saw.
        """
        self._picture.show_frame(pixels, frame)
        text = status_text(hands)
        # Set only on a change: 30 times a second, a label that is told its
        # text again still re-lays itself out.
        if text != self._status.text():
            self._status.setText(text)

    def show_no_camera(self) -> None:
        self._show_message(NO_CAMERA_TEXT)

    def show_camera_lost(self) -> None:
        self._show_message(CAMERA_LOST_TEXT)

    def _show_message(self, text: str) -> None:
        # The last picture goes too: a frozen frame would look like a camera
        # that is still working.
        self._picture.show_frame(None, None)
        self._status.setText(text)

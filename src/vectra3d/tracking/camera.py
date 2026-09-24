"""Opening the webcam.

OpenCV is used only to read frames; Qt draws them. The app must work fully
with no camera at all (F-02), so a camera that is missing or refuses to open
is an ordinary outcome here, reported as `None`, not an error.
"""

from __future__ import annotations

import cv2

# The laptop's built-in camera, or the first USB one.
DEFAULT_CAMERA = 0

# DirectShow rather than OpenCV's default Windows backend (Media Foundation).
# Measured on the target laptop: DirectShow opened the camera in 0.8 s and
# delivered its first frame at 0.84 s; Media Foundation took 2.5 s and 3.0 s,
# at the same 640x480 and 30 fps. `library-docs.md` suggests this for slow
# opening on Windows.
BACKEND = cv2.CAP_DSHOW


def open_camera(index: int = DEFAULT_CAMERA) -> cv2.VideoCapture | None:
    """Open a webcam, or return `None` if there is none to open."""
    capture = cv2.VideoCapture(index, BACKEND)
    if not capture.isOpened():
        capture.release()
        return None
    return capture

"""Short transitions in the 3D view.

At the moment there is one: when a vector changes and the temporary result is
worked out again, the result arrow slides to its new value over 150 ms rather
than jumping there (`interaction-spec.md` section 10). The duration is
`config.RESULT_TRANSITION_MS`.

Why it is worth animating at all, when the scene rescale deliberately is not
(G1.2): a rescale changes everything in the scene at once, and moving the
parts separately made the world look wrong for the whole 300 ms. A result is
one arrow moving while everything around it stays still, which is exactly the
case where a short slide tells the student *that* something responded to their
edit, and which one.

**Measured on the installed PySide6 6.11.2:** a 150 ms `QVariantAnimation`
emits about **9** steps, and its first `valueChanged` already carries a
progress of roughly 0.21 rather than 0. So the arrow starts a fifth of the way
along instead of at its old position. At this duration that reads as a quick
move rather than a jump, and both numbers are recorded in `library-docs.md`
rather than worked around: driving it from a `QTimer` would mean writing the
easing and the clock by hand to fix something nobody can see.

The interpolation itself is a plain function with no Qt in it, so the maths
that decides where the arrow is on each step is tested without a window.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QObject, QVariantAnimation

from vectra3d import config
from vectra3d.core.vector_math import Triple


def interpolate(start: Triple, end: Triple, progress: float) -> Triple:
    """Where the arrow is partway between two values.

    `progress` runs from 0 at the start to 1 at the end and is clamped, so a
    value slightly outside the range - which an easing curve can produce -
    cannot throw the arrow past where it is going.
    """
    fraction = min(1.0, max(0.0, progress))
    return (
        start[0] + (end[0] - start[0]) * fraction,
        start[1] + (end[1] - start[1]) * fraction,
        start[2] + (end[2] - start[2]) * fraction,
    )


class ComponentTransition(QObject):
    """Slides one set of components to another, reporting each step.

    Starting a new transition while one is running takes over from wherever
    the arrow currently is, rather than from where the last one began. A
    student dragging a value through several edits in quick succession would
    otherwise see the arrow jump back before setting off again.
    """

    def __init__(
        self, on_step: Callable[[Triple], None], parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._on_step = on_step
        self._current: Triple | None = None
        self._from: Triple = (0.0, 0.0, 0.0)
        self._to: Triple = (0.0, 0.0, 0.0)
        self._animation = QVariantAnimation(self)
        self._animation.setDuration(config.RESULT_TRANSITION_MS)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.valueChanged.connect(self._step)

    def move_to(self, components: Triple) -> None:
        """Slide to these components, or jump if there is nowhere to slide from."""
        self._animation.stop()

        if self._current is None:
            # Nothing was showing, so there is no journey to animate: a result
            # appearing for the first time should simply be there.
            self._settle(components)
            return

        self._from = self._current
        self._to = components
        self._animation.start()

    def cancel(self) -> None:
        """Stop animating and forget where the arrow was.

        Called when the result goes, so the next result appears where it
        belongs rather than sliding from the last one's position.
        """
        self._animation.stop()
        self._current = None

    def _step(self, progress: float) -> None:
        position = interpolate(self._from, self._to, float(progress))
        self._current = position
        self._on_step(position)

    def _settle(self, components: Triple) -> None:
        self._current = components
        self._on_step(components)

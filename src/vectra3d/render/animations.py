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

from collections.abc import Callable, Sequence

from PySide6.QtCore import (
    QEasingCurve,
    QObject,
    QSequentialAnimationGroup,
    QVariantAnimation,
)

from vectra3d import config
from vectra3d.core.vector_math import Triple

# Where every vector's tail sits when the chain is packed away.
ORIGIN_POINT: Triple = (0.0, 0.0, 0.0)


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


def chain_tails(components: Sequence[Triple]) -> tuple[Triple, ...]:
    """Where each vector's tail sits once the chain is laid out head to tail.

    The first vector stays at the origin; every one after it begins where the
    previous one ended. So each tail is the running sum of everything before
    it, and the head of the last vector lands exactly on the resultant - which
    is the whole point the animation is making.

    Pure geometry, with no Qt and no store in sight, so the shape of the chain
    can be checked against hand-worked examples without opening a window.
    """
    tails: list[Triple] = []
    running: Triple = (0.0, 0.0, 0.0)
    for component in components:
        tails.append(running)
        running = (
            running[0] + component[0],
            running[1] + component[1],
            running[2] + component[2],
        )
    return tuple(tails)


class HeadToTail(QObject):
    """Plays the four phases that show how a resultant is built (F-15).

    The phases and their durations are `interaction-spec.md` section 10, and
    the four times live in `config.py`:

    1. **slide** - the vectors move from the origin into a head-to-tail chain;
    2. **draw** - the resultant grows from the origin to the last head;
    3. **pause** - nothing moves, so there is time to read it;
    4. **return** - the vectors slide back to the origin.

    **It never changes a vector.** Each frame reports where every vector's tail
    should be *drawn*, and how much of the resultant to show. The window draws
    copies at those tails; the store is not involved and never hears from this
    class. That is F-15's "the animation does not permanently move or change
    any vector", made true by construction rather than by being careful.

    Anything that changes the store cancels the run, and the window then
    redraws the real scene. Rather than teaching this class about edits,
    deletions and undo, the rule is simply that the store wins.
    """

    def __init__(
        self,
        on_frame: Callable[[tuple[Triple, ...], float], None],
        on_finished: Callable[[], None],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._on_frame = on_frame
        self._on_finished = on_finished
        self._components: tuple[Triple, ...] = ()
        self._tails: tuple[Triple, ...] = ()

        self._group = QSequentialAnimationGroup(self)
        self._slide = self._phase(config.HEAD_TO_TAIL_SLIDE_S)
        self._draw = self._phase(config.HEAD_TO_TAIL_DRAW_S)
        self._return = self._phase(config.HEAD_TO_TAIL_RETURN_S)

        self._slide.valueChanged.connect(self._on_slide)
        self._draw.valueChanged.connect(self._on_draw)
        self._return.valueChanged.connect(self._on_return)

        self._group.addAnimation(self._slide)
        self._group.addAnimation(self._draw)
        # A real phase with nothing moving, not a shortcut: the hold is what
        # gives the student time to read the chain before it comes apart.
        self._group.addPause(int(config.HEAD_TO_TAIL_PAUSE_S * 1000))
        self._group.addAnimation(self._return)
        self._group.finished.connect(self._finish)

    @property
    def is_playing(self) -> bool:
        return self._group.state() == QSequentialAnimationGroup.State.Running

    def play(self, components: Sequence[Triple]) -> None:
        """Start the explanation for these vectors, in this order."""
        self._group.stop()
        self._components = tuple(components)
        self._tails = chain_tails(self._components)
        self._group.start()

    def cancel(self) -> None:
        """Stop at once and tell the window to put the real scene back."""
        if not self.is_playing:
            return
        self._group.stop()
        self._finish()

    def _phase(self, seconds: float) -> QVariantAnimation:
        phase = QVariantAnimation(self)
        phase.setDuration(int(seconds * 1000))
        phase.setStartValue(0.0)
        phase.setEndValue(1.0)
        phase.setEasingCurve(QEasingCurve.Type.InOutQuad)
        return phase

    def _on_slide(self, progress: float) -> None:
        self._frame_at(float(progress), drawn=0.0)

    def _on_draw(self, progress: float) -> None:
        # The chain is fully formed by now; only the resultant is growing.
        self._frame_at(1.0, drawn=float(progress))

    def _on_return(self, progress: float) -> None:
        # Backwards along the same path, with the resultant staying drawn so
        # the answer is still there as the chain comes apart.
        self._frame_at(1.0 - float(progress), drawn=1.0)

    def _frame_at(self, spread: float, drawn: float) -> None:
        """Report one frame: every tail partway out, and how much of the sum."""
        tails = tuple(
            interpolate(ORIGIN_POINT, tail, spread) for tail in self._tails
        )
        self._on_frame(tails, drawn)

    def _finish(self) -> None:
        self._components = ()
        self._tails = ()
        self._on_finished()

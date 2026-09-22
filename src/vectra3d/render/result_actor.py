"""Drawing the temporary operation result: one arrow, labelled with its sum.

A result is an arrow like any vector, so this follows `vector_actor.py`
closely and borrows its proportions rather than inventing new ones - the
result should read as the same kind of object as the vectors it came from,
not as a different sort of thing that happens to be in the scene.

Three things make it visibly *not* a regular vector:

- it is drawn in the one reserved colour (`naming.RESULT_COLOR`), which no
  vector ever uses, so its identity does not depend on reading the label;
- its label is its expression, "A + B", rather than a single letter;
- it is never haloed, because it cannot be the active vector.

It is deliberately drawn a little heavier than a vector. The reserved colour
is near-black against a light background, which already stands out, but the
result is the answer the student asked for and should not be the thinnest
thing on screen.
"""

from __future__ import annotations

import numpy as np
import pyvista as pv

from vectra3d.render.vector_actor import (
    LETTER_FONT_SIZE,
    LETTER_OFFSET,
    SHAFT_RADIUS,
    TIP_LENGTH,
    TIP_RADIUS,
)
from vectra3d.state import naming
from vectra3d.state.models import Result

# The result arrow against a vector arrow. Enough to carry the eye to the
# answer without making it look like a different kind of object.
WEIGHT = 1.5

ACTOR_NAME = "result"
LABEL_NAME = "result-label"


def label_position(result: Result) -> tuple[float, float, float]:
    """Where the expression sits: just past the head, along the result's line.

    The same rule as a vector's letter, so the two never disagree about where
    a label belongs. An expression is several characters wide where a letter
    is one, but it is offset along the arrow rather than sideways, so it
    cannot land on the arrow it belongs to.
    """
    tail = np.array(result.tail, dtype=float)
    head = tail + np.array(result.components, dtype=float)
    along = head - tail
    length = float(np.linalg.norm(along))
    if length == 0.0:
        return tuple(float(value) for value in head)
    return tuple(float(value) for value in head + along * LETTER_OFFSET)


class ResultActor:
    """Keeps the result arrow in the 3D view matching the one in the store."""

    def __init__(self, plotter: pv.Plotter) -> None:
        self._plotter = plotter
        self._drawn = False

    def draw(self, result: Result | None) -> None:
        """Draw the result, or take it away if there is none.

        Nothing renders here. The window redraws the vectors, the overlays and
        the result together and renders once, which is what stops the scene
        blinking (G1.2).
        """
        if result is None:
            self._remove()
            return

        components = np.array(result.components, dtype=float)
        length = float(np.linalg.norm(components))
        if length == 0.0:
            # A resultant of vectors that cancel is the zero vector, which has
            # no direction to draw (`interaction-spec.md` 2.4). This is an
            # ordinary case, not a defensive one - F-15 names it - and the
            # info panel still shows the result and its numbers. There is
            # simply no arrow to point anywhere.
            self._remove()
            return

        tail = np.array(result.tail, dtype=float)
        self._plotter.add_mesh(
            pv.Arrow(
                start=tail,
                direction=components,
                scale=length,
                shaft_radius=SHAFT_RADIUS * WEIGHT,
                tip_radius=TIP_RADIUS * WEIGHT,
                tip_length=TIP_LENGTH,
            ),
            color=naming.RESULT_COLOR,
            name=ACTOR_NAME,
            render=False,
        )

        label = pv.Label(
            text=result.expression,
            position=label_position(result),
            size=LETTER_FONT_SIZE,
        )
        label.prop.color = naming.RESULT_COLOR
        self._plotter.add_actor(
            label,
            name=LABEL_NAME,
            reset_camera=False,
            render=False,
        )
        self._drawn = True

    def _remove(self) -> None:
        if not self._drawn:
            return
        self._plotter.remove_actor(ACTOR_NAME, render=False)
        self._plotter.remove_actor(LABEL_NAME, render=False)
        self._drawn = False

"""Drawing the vectors themselves: one arrow each, with its letter.

The active vector is wrapped in a translucent copy of itself, a glow
(`interaction-spec.md` section 10), so the student can see at a glance which
one the panel and, later, their hands are acting on.

Arrow proportions are fractions of the vector's own length rather than of the
scene extent, so a short vector is a small arrow instead of a stubby barrel in
a large world.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pyvista as pv

from vectra3d.core.vector_math import magnitude as magnitude_of
from vectra3d.state import naming
from vectra3d.state.models import Vector

# Arrow proportions, as fractions of the vector's own length. Much slimmer
# than PyVista's defaults (a shaft of 0.05 and a tip of 0.1), which next to
# one-pixel axis lines and a light grid look like pipes rather than arrows.
SHAFT_RADIUS = 0.007
TIP_RADIUS = 0.018
TIP_LENGTH = 0.060

# The active vector is wrapped in a translucent copy of itself, which reads as
# a glow around it (`interaction-spec.md` section 10). Drawing it thicker was
# the first attempt and was worse: thickness then means two things at once,
# and the active vector looked like a different kind of object rather than the
# same one, singled out.
HALO_SCALE = 3.4
HALO_OPACITY = 0.22
# When a steered vector snaps onto an axis or plane its halo flashes brighter
# for a moment (`interaction-spec.md` section 10). The halo rather than the
# axis, because a plane has no single line to flash.
SNAP_FLASH_OPACITY = 0.6
SNAP_FLASH_MS = 300

LETTER_FONT_SIZE = 15
# How far past the head the letter sits, as a fraction of the arrow's length.
LETTER_OFFSET = 0.08


def letter_position(vector: Vector) -> tuple[float, float, float]:
    """Where a vector's letter sits: just past its head, along its own line.

    Offset from the head in the vector's own direction rather than scaled
    outward from the origin. The two are the same while every tail is at the
    origin, which is all the MVP has, but only this one stays correct for
    free vectors, whose tails move away from it (`project-overview.md`).
    """
    tail = np.array(vector.tail, dtype=float)
    head = tail + np.array(vector.components, dtype=float)
    along = head - tail
    length = magnitude_of(tuple(along))
    if length == 0.0:
        return tuple(float(v) for v in head)
    return tuple(float(v) for v in head + along * LETTER_OFFSET)


class VectorActors:
    """Keeps the arrows in the 3D view matching the vectors in the store."""

    def __init__(self, plotter: pv.Plotter) -> None:
        self._plotter = plotter
        self._drawn: set[str] = set()

    def draw(
        self,
        vectors: Sequence[Vector],
        active_name: str | None,
        labels: Mapping[str, str] | None = None,
    ) -> None:
        """Redraw every vector, and remove the ones that are gone.

        Actors are named after the vector, so PyVista replaces them in place.
        Nothing renders until the whole set is done: rendering per actor is
        what made the scene blink in G1.2.

        `labels` overrides what is written beside a vector, by name. It exists
        for the head-to-tail animation, where the second term of `A - B` is B
        pointing the other way and has to read "-B"; calling it "B" would put
        a letter on an arrow pointing away from where B actually points. The
        colour still comes from the vector's own name, because it is still
        that vector.
        """
        wanted = {vector.name for vector in vectors}
        for name in self._drawn - wanted:
            self._plotter.remove_actor(f"vector-{name}", render=False)
            self._plotter.remove_actor(f"letter-{name}", render=False)

        # Only one vector is active at a time, so every halo goes and at most
        # one comes back. Cheaper than working out which one moved, and it
        # covers the vector that was both active and just deleted.
        for name in self._drawn | wanted:
            self._plotter.remove_actor(f"halo-{name}", render=False)

        self._drawn = wanted

        for vector in vectors:
            self._draw_one(
                vector,
                vector.name == active_name,
                (labels or {}).get(vector.name, vector.name),
            )

        self._plotter.render()

    def redraw(
        self, vector: Vector, is_active: bool, label_text: str, flash: bool = False
    ) -> None:
        """Redraw one vector and leave every other actor alone. Does not render.

        For a vector being moved by hand, which changes 30 times a second:
        rebuilding all ten arrows each frame measured 90 ms, most of a frame
        spent on arrows that had not moved. Its halo is replaced here too,
        since the moving vector is the active one; `flash` draws it brighter,
        for a snap.
        """
        self._plotter.remove_actor(f"halo-{vector.name}", render=False)
        self._drawn.add(vector.name)
        self._draw_one(vector, is_active, label_text, flash)

    def _draw_one(
        self, vector: Vector, is_active: bool, label_text: str, flash: bool = False
    ) -> None:
        tail = np.array(vector.tail, dtype=float)
        head = tail + np.array(vector.components, dtype=float)
        length = magnitude_of(tuple(head - tail))
        color = naming.color_for(vector.name)

        if length == 0.0:
            # A zero vector has no direction to draw (`interaction-spec.md`
            # 2.4). It still exists, still has a name and a row in the info
            # panel; there is simply no arrow. A result of A - A can be saved
            # as a vector, so this is a real case, not a defensive one.
            self._plotter.remove_actor(f"vector-{vector.name}", render=False)
            self._plotter.remove_actor(f"letter-{vector.name}", render=False)
            return

        def arrow(weight: float) -> pv.PolyData:
            return pv.Arrow(
                start=tail,
                direction=head - tail,
                scale=length,
                shaft_radius=SHAFT_RADIUS * weight,
                tip_radius=TIP_RADIUS * weight,
                tip_length=TIP_LENGTH,
            )

        if is_active:
            self._plotter.add_mesh(
                arrow(HALO_SCALE),
                color=color,
                opacity=SNAP_FLASH_OPACITY if flash else HALO_OPACITY,
                lighting=False,
                name=f"halo-{vector.name}",
                render=False,
            )

        self._plotter.add_mesh(
            arrow(1.0),
            color=color,
            name=f"vector-{vector.name}",
            render=False,
        )

        label = pv.Label(
            text=label_text,
            position=letter_position(vector),
            size=LETTER_FONT_SIZE,
        )
        label.prop.color = color
        self._plotter.add_actor(
            label,
            name=f"letter-{vector.name}",
            reset_camera=False,
            render=False,
        )

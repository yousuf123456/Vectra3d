"""Drawing what a vector is made of: its components, and the box they build.

When a vector has its components switched on (F-13a), three things are drawn:

- **three arrows along the axes**, carrying its x, y and z parts, in the axis
  colours red, green and blue,
- **the outline box**: the cuboid whose space diagonal is the vector, drawn
  dashed, which is what shows the three parts adding up to the whole,
- **a label on each arrow** with that component's value.

Only nine of the cuboid's twelve edges are drawn. The other three run along
the axes from the origin, and those *are* the component arrows; drawing a grey
dash along a coloured arrow at these line widths reads as a muddied colour
rather than as two separate things.

The geometry is plain functions over a triple of numbers, tested without a
plotter. They work in tail-relative coordinates - offsets from wherever the
vector starts - and the class adds the tail, so nothing here has to change
when free vectors arrive (`project-overview.md`).

PyVista exposes no line-stipple setting, so a dash is geometry: each edge is
cut into short segments, and all of a vector's segments are batched into one
mesh so the whole box stays a single actor.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pyvista as pv

from vectra3d.core.formatting import format_number
from vectra3d.render.scene import AXIS_COLORS
from vectra3d.render.vector_actor import SHAFT_RADIUS, TIP_LENGTH, TIP_RADIUS
from vectra3d.state.models import Point, Vector

Triple = tuple[float, float, float]

# How thick a component arrow is, relative to the vector's own arrow.
#
# The thickness is worked out from the *vector's* magnitude, not from each
# component's own length, which is what the first version did and why the
# arrows were invisible: a component is shorter than the vector, so scaling
# its radius by its own length made it thinner than the axis line it sits on,
# and it read as part of the axis. Sizing all three from one number also
# makes them the same thickness as each other, which is what lets them be
# compared.
#
# F-13a fixes their colours to the axis colours, so thickness is what tells
# an arrow from the axis underneath it. It is also the only thing keeping
# them from looking like the main object, so they are held back two other
# ways instead of being made thin again: they are partly transparent, and
# they are flat-shaded, so they read as workings drawn onto the scene rather
# than as solid objects in it.
COMPONENT_WEIGHT = 1.3

# Solid enough to be seen against the axis line, light enough that the
# vector's own arrow stays the thing being looked at. Chosen by rendering
# the scene and looking at it: at 0.9 thickness and 0.45 opacity the x and y
# arrows disappeared into the axes again, which is the fault this whole
# treatment exists to avoid.
COMPONENT_OPACITY = 0.7

# An arrowhead no longer than half its own shaft, whatever the vector's
# magnitude suggests - otherwise a short component is all head.
MAX_TIP_FRACTION = 0.5

# Dash and gap, as fractions of the vector's own magnitude - the same idea as
# the arrow proportions in `vector_actor.py`, so a small vector gets a small
# dash rather than one dash per edge.
DASH_FRACTION = 0.035
MIN_DASHES = 2

BOX_COLOR = "#999999"
BOX_LINE_WIDTH = 1.0

LABEL_FONT_SIZE = 12
# How far off its arrow a component's value sits, as a fraction of the
# vector's magnitude. Large enough to clear the axis tick numbers, which run
# along the same lines and which the first version sat straight on top of.
LABEL_OFFSET = 0.16

# How far along its own arrow a value sits, as a fraction of that component.
ALONG_ARROW = 0.8

# Rounding used only to decide whether two corners of the box are the same
# point. Far finer than anything the display shows, and never applied to a
# value that is drawn or stored.
_SAME_POINT = 9


def component_offsets(components: Triple) -> tuple[Triple, Triple, Triple]:
    """The three component vectors, as offsets from the tail.

    (x, y, z) becomes (x, 0, 0), (0, y, 0) and (0, 0, z) - which is what
    "resolving into components" means, and what the three arrows draw.
    """
    x, y, z = components
    return ((x, 0.0, 0.0), (0.0, y, 0.0), (0.0, 0.0, z))


def box_edges(components: Triple) -> tuple[tuple[Triple, Triple], ...]:
    """The dashed edges of the outline box, as tail-relative point pairs.

    Nine edges for a vector with all three components, because the three
    running along the axes from the tail are the component arrows instead.

    Fewer when the box is flat. A vector lying in a coordinate plane has no
    depth, so its cuboid collapses to a rectangle whose two faces sit on top
    of each other; the duplicates are dropped rather than drawn twice. A
    vector lying along an axis collapses it to a line, and there is nothing
    left to draw once the arrows are taken out.
    """
    x, y, z = components
    corners = {
        "x": (x, 0.0, 0.0),
        "y": (0.0, y, 0.0),
        "z": (0.0, 0.0, z),
    }

    # Every edge of the cuboid: from each of the eight corners, the three
    # edges leaving it, built as "this corner, plus one more component".
    edges: dict[tuple[Triple, Triple], tuple[Triple, Triple]] = {}
    for present in ((), ("x",), ("y",), ("z",), ("x", "y"), ("x", "z"), ("y", "z")):
        start = _sum_of(corners, present)
        for axis in ("x", "y", "z"):
            if axis in present:
                continue
            end = _sum_of(corners, (*present, axis))
            if _key(start) == _key(end):
                # A zero component: this edge has no length at all.
                continue
            if _is_arrow(start, end, corners):
                # An edge along an axis from the tail, which the component
                # arrow already draws.
                continue
            edges[_edge_key(start, end)] = (start, end)

    return tuple(edges.values())


def dash_segments(
    start: Triple, end: Triple, dash: float
) -> tuple[tuple[Triple, Triple], ...]:
    """Cut one edge into dashes: short drawn pieces with gaps between them.

    PyVista has no dashed-line style, so the dashes are made of geometry.
    Always at least `MIN_DASHES`, so a short edge still reads as dashed
    rather than as one solid stroke.
    """
    first = np.array(start, dtype=float)
    last = np.array(end, dtype=float)
    length = float(np.linalg.norm(last - first))
    if length == 0.0 or dash <= 0.0:
        return ()

    # A dash and its following gap take two slots, and the edge ends on a
    # dash, so n dashes need 2n - 1 slots.
    count = max(MIN_DASHES, int(round(length / (dash * 2))))
    slot = 1.0 / (2 * count - 1)

    segments = []
    for index in range(count):
        begin = (2 * index) * slot
        finish = begin + slot
        segments.append(
            (
                tuple(first + (last - first) * begin),
                tuple(first + (last - first) * min(finish, 1.0)),
            )
        )
    return tuple(segments)


def label_text(components: Triple) -> tuple[str, str, str]:
    """What each component arrow says: its value, as the info panel shows it."""
    return (
        format_number(components[0]),
        format_number(components[1]),
        format_number(components[2]),
    )


def label_positions(components: Triple, magnitude: float) -> tuple[Triple, ...]:
    """Where each component's value sits: beside its own arrow, clear of
    everything else drawn along the same line.

    Two things already run along these axes: the axis tick numbers, which
    hang below the axis line, and for the z arrow the vector itself. So the
    x and y values are lifted straight up in z, above their arrows and clear
    of the numbers below them, and the z value is pushed out horizontally,
    away from whichever quadrant the vector is leaning into.

    Offsetting into two negative axes at once - the first attempt - reads as
    no offset at all from many angles, because the two displacements cancel
    in projection and the label lands back on the origin.

    Well down its own arrow rather than at the midpoint, because near the
    tail all three arrows and the vector itself converge, and a label placed
    in that cluster ends up behind one of them whatever direction it is
    nudged in.
    """
    offset = magnitude * LABEL_OFFSET
    x, y, z = components
    return (
        (x * ALONG_ARROW, 0.0, offset),
        (0.0, y * ALONG_ARROW, offset),
        (-_away(x) * offset, -_away(y) * offset, z * ALONG_ARROW),
    )


def _away(value: float) -> float:
    """Which way to lean to get clear of a component: +1 unless it is negative.

    A zero component has no side to avoid, so either answer is as good; +1
    keeps the label on the side the default camera is looking from.
    """
    return -1.0 if value < 0.0 else 1.0


def _sum_of(corners: dict[str, Triple], axes: Sequence[str]) -> Triple:
    total = np.zeros(3)
    for axis in axes:
        total = total + np.array(corners[axis], dtype=float)
    return (float(total[0]), float(total[1]), float(total[2]))


def _key(point: Triple) -> tuple[float, float, float]:
    return (
        round(point[0], _SAME_POINT),
        round(point[1], _SAME_POINT),
        round(point[2], _SAME_POINT),
    )


def _edge_key(start: Triple, end: Triple) -> tuple[Triple, Triple]:
    """An edge's identity, independent of which end it was built from."""
    first, second = _key(start), _key(end)
    return (first, second) if first <= second else (second, first)


def _is_arrow(start: Triple, end: Triple, corners: dict[str, Triple]) -> bool:
    """Whether this edge is one the component arrows already draw.

    Decided from where the edge *is*, not from how it was built. When a
    component is zero the cuboid is flat, and the same edge can be reached
    both directly from the tail and by way of the collapsed side - so a test
    based on the construction path lets the second one through.
    """
    if _key(start) != (0.0, 0.0, 0.0):
        return False
    return _key(end) in {_key(corner) for corner in corners.values()}


class ComponentOverlays:
    """Keeps the component arrows, boxes and labels matching the store."""

    def __init__(self, plotter: pv.Plotter) -> None:
        self._plotter = plotter
        self._drawn: set[str] = set()

    def draw(self, vectors: Sequence[Vector], shown: str | None) -> None:
        """Draw the one vector showing its components, and remove any others.

        At most one vector shows them at a time (`VectorStore` explains why),
        but this still clears by name rather than assuming what was drawn
        before, so switching from one vector to another cannot leave the
        first one's arrows behind.

        Actors are named after the vector, so PyVista replaces them in place.
        Nothing renders until the whole set is done: rendering per actor is
        what made the scene blink in G1.2.
        """
        wanted = {vector.name for vector in vectors if vector.name == shown}
        for name in self._drawn - wanted:
            self._remove(name)
        self._drawn = wanted

        for vector in vectors:
            if vector.name in wanted:
                self._draw_one(vector)

        self._plotter.render()

    def _remove(self, name: str) -> None:
        self._plotter.remove_actor(f"box-{name}", render=False)
        for axis in AXIS_COLORS:
            self._plotter.remove_actor(f"component-{axis}-{name}", render=False)
            self._plotter.remove_actor(f"componentlabel-{axis}-{name}", render=False)

    def _draw_one(self, vector: Vector) -> None:
        tail = np.array(vector.tail, dtype=float)
        components = vector.components
        magnitude = float(np.linalg.norm(np.array(components, dtype=float)))
        if magnitude == 0.0:
            # A zero vector has no parts to show. It can exist - an operation
            # result of A - A can be saved as one (F-16).
            self._remove(vector.name)
            return

        self._draw_arrows(vector, tail, magnitude)
        self._draw_box(vector, tail, magnitude)
        self._draw_labels(vector, tail, magnitude)

    def _draw_arrows(self, vector: Vector, tail: np.ndarray, magnitude: float) -> None:
        offsets = component_offsets(vector.components)
        for (axis, color), offset in zip(AXIS_COLORS.items(), offsets):
            name = f"component-{axis}-{vector.name}"
            length = float(np.linalg.norm(np.array(offset, dtype=float)))
            if length == 0.0:
                # A component of zero is a real answer, and an arrow of no
                # length is not a way of saying it. The label still does.
                self._plotter.remove_actor(name, render=False)
                continue

            # pv.Arrow takes its radii as fractions of the arrow's own
            # length, so an absolute size has to be divided back out.
            shaft = SHAFT_RADIUS * magnitude * COMPONENT_WEIGHT
            tip = TIP_RADIUS * magnitude * COMPONENT_WEIGHT
            self._plotter.add_mesh(
                pv.Arrow(
                    start=tail,
                    direction=offset,
                    scale=length,
                    shaft_radius=shaft / length,
                    tip_radius=tip / length,
                    tip_length=min(
                        MAX_TIP_FRACTION, TIP_LENGTH * magnitude / length
                    ),
                ),
                color=color,
                opacity=COMPONENT_OPACITY,
                # Flat, not lit: a lit arrow has highlights and shading that
                # make it read as a solid object competing with the vector.
                lighting=False,
                name=name,
                render=False,
            )

    def _draw_box(self, vector: Vector, tail: np.ndarray, magnitude: float) -> None:
        name = f"box-{vector.name}"
        dash = magnitude * DASH_FRACTION
        pairs: list[tuple[Point, Point]] = []
        for start, end in box_edges(vector.components):
            for piece_start, piece_end in dash_segments(start, end, dash):
                pairs.append(
                    (
                        tuple(tail + np.array(piece_start)),
                        tuple(tail + np.array(piece_end)),
                    )
                )

        if not pairs:
            # A vector lying along an axis: the box is a line, and the arrow
            # is already drawing it.
            self._plotter.remove_actor(name, render=False)
            return

        points = np.array([point for pair in pairs for point in pair], dtype=float)
        lines = np.hstack(
            [[2, 2 * index, 2 * index + 1] for index in range(len(pairs))]
        )
        self._plotter.add_mesh(
            pv.PolyData(points, lines=lines),
            color=BOX_COLOR,
            line_width=BOX_LINE_WIDTH,
            name=name,
            render=False,
        )

    def _draw_labels(self, vector: Vector, tail: np.ndarray, magnitude: float) -> None:
        texts = label_text(vector.components)
        positions = label_positions(vector.components, magnitude)
        for (axis, color), text, position in zip(
            AXIS_COLORS.items(), texts, positions
        ):
            label = pv.Label(
                text=text,
                position=tuple(tail + np.array(position)),
                size=LABEL_FONT_SIZE,
            )
            label.prop.color = color
            self._plotter.add_actor(
                label, name=f"componentlabel-{axis}-{vector.name}", render=False
            )

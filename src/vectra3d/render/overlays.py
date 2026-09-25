"""Drawing what a vector is made of: its components, and the box they build.

Three overlays live here. The third, the **angle arcs** showing the active
vector's theta and phi, is always on and is described where it is defined,
at the end.

**Components** (F-13a). When a vector has its components switched on, three
things are drawn:

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

**Projections** (F-14). A vector's shadows on the XY, YZ and XZ planes: each
one an arrow in the vector's own colour, with a dashed line dropping from the
head to its tip. The colour says whose shadow it is; the drop line is what
makes it read as a shadow rather than as another vector from the origin.

PyVista exposes no line-stipple setting, so a dash is geometry: each edge is
cut into short segments, and all of a vector's segments are batched into one
mesh so the whole box stays a single actor.
"""

from __future__ import annotations

import math
import os
from collections.abc import Sequence

import numpy as np
import pyvista as pv

from vectra3d.core.formatting import format_angle, format_number
from vectra3d.core.spherical import to_spherical
from vectra3d.render.scene import AXIS_COLORS
from vectra3d.render.vector_actor import SHAFT_RADIUS, TIP_LENGTH, TIP_RADIUS
from vectra3d.core.vector_math import magnitude as magnitude_of
from vectra3d.core.vector_math import unit_vector
from vectra3d.state import naming
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

# A shadow is drawn in its own vector's colour rather than in grey, so it
# says whose shadow it is without needing a label. Grey is already the
# component box's, and the axis colours are already the component arrows'.
PROJECTION_OPACITY = 0.4
# Shadows are thinner and fainter than the vector itself: they are a
# consequence of it, not a second reading of it, and three at once would
# otherwise crowd the scene. They can be this faint and still read, unlike
# the component arrows, precisely because they are in the vector's own
# colour: nothing else in the scene is that colour, so there is no axis line
# for them to disappear into. Chosen by rendering and looking.
PROJECTION_WEIGHT = 0.55

# The three planes a vector is projected onto.
PROJECTION_PLANES = ("xy", "yz", "xz")

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


def projection_offsets(components: Triple) -> tuple[Triple, Triple, Triple]:
    """The vector's shadows on the XY, YZ and XZ planes (F-14).

    A shadow on a plane is the vector with the one component perpendicular
    to that plane dropped: flattened onto XY, a vector keeps its x and y and
    loses its height. Which is what a shadow is - what is left when one
    direction stops counting.

        XY -> (x, y, 0)     YZ -> (0, y, z)     XZ -> (x, 0, z)

    A vector already lying in one of the planes is its own shadow there, and
    a vector along an axis casts the same shadow on the two planes that
    contain it and nothing on the third.
    """
    x, y, z = components
    return ((x, y, 0.0), (0.0, y, z), (x, 0.0, z))


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
    length = magnitude_of(tuple(last - first))
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


class ProjectionOverlays:
    """Keeps each vector's shadows on the three planes matching the store.

    Its own class rather than part of `ComponentOverlays`, because the two
    overlays are switched on and off separately and neither should have to
    know whether the other is showing.
    """

    def __init__(self, plotter: pv.Plotter) -> None:
        self._plotter = plotter
        self._drawn: set[str] = set()

    def draw(self, vectors: Sequence[Vector], shown: str | None) -> None:
        """Draw the one vector casting shadows, and remove any others."""
        wanted = {vector.name for vector in vectors if vector.name == shown}
        for name in self._drawn - wanted:
            self._remove(name)
        self._drawn = wanted

        for vector in vectors:
            if vector.name in wanted:
                self._draw_one(vector)

        self._plotter.render()

    def _remove(self, name: str) -> None:
        for plane in PROJECTION_PLANES:
            self._plotter.remove_actor(f"shadow-{plane}-{name}", render=False)
        self._plotter.remove_actor(f"drop-{name}", render=False)

    def _draw_one(self, vector: Vector) -> None:
        tail = np.array(vector.tail, dtype=float)
        magnitude = magnitude_of(vector.components)
        if magnitude == 0.0:
            self._remove(vector.name)
            return

        color = naming.color_for(vector.name)
        shadows = projection_offsets(vector.components)
        self._draw_shadows(vector, tail, magnitude, shadows, color)
        self._draw_drops(vector, tail, magnitude, shadows, color)

    def _draw_shadows(
        self,
        vector: Vector,
        tail: np.ndarray,
        magnitude: float,
        shadows: Sequence[Triple],
        color: str,
    ) -> None:
        for plane, offset in zip(PROJECTION_PLANES, shadows):
            name = f"shadow-{plane}-{vector.name}"
            length = magnitude_of(offset)
            if length == 0.0:
                # The vector is perpendicular to this plane, so its shadow
                # there is a point. Nothing to draw.
                self._plotter.remove_actor(name, render=False)
                continue

            shaft = SHAFT_RADIUS * magnitude * PROJECTION_WEIGHT
            tip = TIP_RADIUS * magnitude * PROJECTION_WEIGHT
            self._plotter.add_mesh(
                pv.Arrow(
                    start=tail,
                    direction=offset,
                    scale=length,
                    shaft_radius=shaft / length,
                    tip_radius=tip / length,
                    tip_length=min(MAX_TIP_FRACTION, TIP_LENGTH * magnitude / length),
                ),
                color=color,
                opacity=PROJECTION_OPACITY,
                lighting=False,
                name=name,
                render=False,
            )

    def _draw_drops(
        self,
        vector: Vector,
        tail: np.ndarray,
        magnitude: float,
        shadows: Sequence[Triple],
        color: str,
    ) -> None:
        """The dashed lines joining the head to each shadow's tip.

        Without them the three shadows read as three more vectors sharing
        the origin, rather than as this one seen from three sides.
        """
        name = f"drop-{vector.name}"
        head = np.array(vector.components, dtype=float)
        dash = magnitude * DASH_FRACTION

        pairs: list[tuple[Point, Point]] = []
        for offset in shadows:
            target = np.array(offset, dtype=float)
            if np.allclose(target, head):
                # The vector lies in this plane, so it is its own shadow
                # there and there is no gap to bridge.
                continue
            if not np.any(target):
                # The vector is perpendicular to this plane, so its shadow
                # is a point at the tail and no arrow was drawn. A drop line
                # to it would run from the head back to the tail - a dashed
                # copy of the vector, lying along the vector.
                continue
            for start, end in dash_segments(tuple(head), tuple(target), dash):
                pairs.append(
                    (tuple(tail + np.array(start)), tuple(tail + np.array(end)))
                )

        if not pairs:
            self._plotter.remove_actor(name, render=False)
            return

        points = np.array([point for pair in pairs for point in pair], dtype=float)
        lines = np.hstack([[2, 2 * i, 2 * i + 1] for i in range(len(pairs))])
        self._plotter.add_mesh(
            pv.PolyData(points, lines=lines),
            color=color,
            opacity=PROJECTION_OPACITY,
            line_width=BOX_LINE_WIDTH,
            name=name,
            render=False,
        )


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
        magnitude = magnitude_of(components)
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
            length = magnitude_of(offset)
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


# --- Angle arcs (interaction-spec.md section 10) ---
#
# The active vector's spherical angles (section 2.3), drawn in the 3D view and
# following it live while a hand moves it: theta as an arc from the +z axis to
# the vector, and phi as an arc in the XY plane from the +x axis round to the
# vector's floor shadow. A dashed guide runs from the origin to that shadow
# and up to the head, so it is visible what phi is measured to.

# How far out the arcs sit, as a fraction of the vector's magnitude: clear of
# the origin marker and the axis numbers near it, well inside the head.
ARC_RADIUS = 0.4
# Points per arc: enough that 360 degrees of phi still reads as a curve.
ARC_POINTS = 64
# Thicker than the one-pixel axes, so an arc is not read as a grid line.
ARC_LINE_WIDTH = 3.5
# How far past its arc's middle an angle's value sits, as a fraction of the
# arc's radius.
ARC_LABEL_OUT = 1.2
# The values are dark bold text on a white box outlined in the vector's
# colour. Text in the vector's own colour was hard to read - the user's report
# at G5.5 - and would be worst for the lightest colours, such as E's yellow.
ARC_LABEL_SIZE = 16
ARC_LABEL_TEXT = "#1F2937"
ARC_LABEL_BACKGROUND = "#FFFFFF"
ARC_LABEL_BACKGROUND_OPACITY = 0.85
THETA = "θ"
PHI = "φ"
# VTK's built-in fonts have no Greek letters: "θ 45.00°" is drawn as
# " 45.00°", degree sign and all. Windows' own Arial has them, and the app is
# Windows only (measured at G5.5; see `library-docs.md`).
GREEK_FONT = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf")
# phi is undefined within this distance of the z axis (section 2.3), measured
# on the unit vector: far finer than anything the display shows.
_ON_Z_AXIS = 1e-12


def theta_arc(components: Triple, radius: float) -> tuple[Triple, ...]:
    """The arc from the +z axis to the vector, `radius` from the tail.

    It runs in the plane holding z and the vector. For a vector along -z that
    plane is not defined, so the arc is drawn through +x in the XZ plane.
    Empty for a vector along +z, where theta is zero and there is nothing to
    draw, and for the zero vector.
    """
    unit = unit_vector(components)
    if unit is None:
        return ()
    theta = math.acos(max(-1.0, min(1.0, unit[2])))
    if theta == 0.0:
        return ()
    # The direction in the XY plane the arc leans towards.
    across = unit_vector((unit[0], unit[1], 0.0)) or (1.0, 0.0, 0.0)
    return tuple(
        (
            radius * math.sin(t) * across[0],
            radius * math.sin(t) * across[1],
            radius * math.cos(t),
        )
        for t in (theta * i / (ARC_POINTS - 1) for i in range(ARC_POINTS))
    )


def phi_arc(components: Triple, radius: float) -> tuple[Triple, ...]:
    """The arc in the XY plane from +x, counterclockwise round to phi.

    Counterclockwise seen from above, the way section 2.3 measures phi, so a
    phi of 270 degrees is three quarters of a turn, not a quarter the other
    way. Empty along the z axis, where phi is undefined.
    """
    angles = _angles(components)
    if angles is None or angles[1] is None:
        return ()
    phi = math.radians(angles[1])
    return tuple(
        (radius * math.cos(s), radius * math.sin(s), 0.0)
        for s in (phi * i / (ARC_POINTS - 1) for i in range(ARC_POINTS))
    )


def angle_labels(components: Triple) -> tuple[str | None, str | None]:
    """What the two arcs say: "θ 45.00°" and "φ 30.00°".

    phi's is None along the z axis, where it is undefined; both are None for
    the zero vector, which has no angles at all.
    """
    angles = _angles(components)
    if angles is None:
        return (None, None)
    theta, phi = angles
    return (
        f"{THETA} {format_angle(theta)}",
        None if phi is None else f"{PHI} {format_angle(phi)}",
    )


def _angles(components: Triple) -> tuple[float, float | None] | None:
    """theta and phi in degrees, with phi None along the z axis."""
    spherical = to_spherical(components)
    if spherical is None:
        return None
    _, theta, phi = spherical
    unit = unit_vector(components)
    flat = math.hypot(unit[0], unit[1])
    return theta, (None if flat < _ON_Z_AXIS else phi)


def _middle(points: Sequence[Triple]) -> Triple | None:
    """Where an arc's value goes: just outside its middle point."""
    if not points:
        return None
    x, y, z = points[len(points) // 2]
    return (x * ARC_LABEL_OUT, y * ARC_LABEL_OUT, z * ARC_LABEL_OUT)


class AngleArcs:
    """Draws the theta and phi arcs for the one active vector.

    One vector at a time, as with components and shadows. Nothing renders
    here: it is redrawn on every frame a hand moves the vector, and the
    window renders once for the whole frame.
    """

    _ACTORS = ("arc-theta", "arc-phi", "arc-guide", "arclabel-theta", "arclabel-phi")

    def __init__(self, plotter: pv.Plotter) -> None:
        self._plotter = plotter

    def draw(self, vector: Vector | None) -> None:
        """Draw the arcs for this vector, or take them away if None."""
        if vector is None or magnitude_of(vector.components) == 0.0:
            for name in self._ACTORS:
                self._plotter.remove_actor(name, render=False)
            return

        tail = np.array(vector.tail, dtype=float)
        radius = magnitude_of(vector.components) * ARC_RADIUS
        color = naming.color_for(vector.name)
        theta_points = theta_arc(vector.components, radius)
        phi_points = phi_arc(vector.components, radius)
        self._draw_line("arc-theta", theta_points, tail, color)
        self._draw_line("arc-phi", phi_points, tail, color)
        self._draw_guide(vector, tail)

        theta_text, phi_text = angle_labels(vector.components)
        self._draw_label("arclabel-theta", theta_text, _middle(theta_points), tail, color)
        self._draw_label("arclabel-phi", phi_text, _middle(phi_points), tail, color)

    def _draw_line(
        self, name: str, points: Sequence[Triple], tail: np.ndarray, color: str
    ) -> None:
        if len(points) < 2:
            self._plotter.remove_actor(name, render=False)
            return
        self._plotter.add_mesh(
            pv.lines_from_points(np.array(points, dtype=float) + tail),
            color=color,
            line_width=ARC_LINE_WIDTH,
            lighting=False,
            name=name,
            render=False,
        )

    def _draw_guide(self, vector: Vector, tail: np.ndarray) -> None:
        """Dashes from the tail to the floor shadow's tip, and up to the head.

        Nothing to guide along the z axis, where the shadow is a point at the
        tail and phi is undefined.
        """
        x, y, _ = vector.components
        shadow = (x, y, 0.0)
        dash = magnitude_of(vector.components) * DASH_FRACTION
        pairs = []
        if (x, y) != (0.0, 0.0):
            pairs.extend(dash_segments((0.0, 0.0, 0.0), shadow, dash))
            # Empty for a vector lying in the XY plane: it is its own shadow.
            pairs.extend(dash_segments(shadow, vector.components, dash))
        if not pairs:
            self._plotter.remove_actor("arc-guide", render=False)
            return
        points = np.array([point for pair in pairs for point in pair], dtype=float)
        lines = np.hstack([[2, 2 * i, 2 * i + 1] for i in range(len(pairs))])
        self._plotter.add_mesh(
            pv.PolyData(points + tail, lines=lines),
            color=BOX_COLOR,
            line_width=BOX_LINE_WIDTH,
            name="arc-guide",
            render=False,
        )

    def _draw_label(
        self,
        name: str,
        text: str | None,
        position: Triple | None,
        tail: np.ndarray,
        color: str,
    ) -> None:
        if text is None or position is None:
            self._plotter.remove_actor(name, render=False)
            return
        label = pv.Label(
            text=text,
            position=tuple(tail + np.array(position)),
            size=ARC_LABEL_SIZE,
        )
        label.prop.set_font_file(GREEK_FONT)
        label.prop.color = ARC_LABEL_TEXT
        label.prop.bold = True
        label.prop.background_color = ARC_LABEL_BACKGROUND
        label.prop.background_opacity = ARC_LABEL_BACKGROUND_OPACITY
        label.prop.frame = True
        label.prop.frame_color = color
        self._plotter.add_actor(label, name=name, reset_camera=False, render=False)

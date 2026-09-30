"""Turning hand positions into vectors (`interaction-spec.md` section 6).

The state machine says what the hands are doing; this works out what that
means for a vector. Pure maths on plain tuples - no camera, no Qt, no
PyVista - so every rule is tested with hand-calculated values.

**Screen-relative directions (6.1).** When creating, a hand moving right in
the mirrored picture means the camera's right in the 3D world, and a hand
moving up means the camera's up, whichever way the view has been turned.
Picture y grows downward, so it is flipped.

**Steering (6.4)** is grab and drag: each frame the vector's two angles
change by as much as the pinching hand moved. Up and down change theta, so
the head always rises towards +z or drops towards -z; sideways changes phi,
turning it round the z axis. A still hand leaves the vector still.

**Snapping (6.5)** happens only on release. While dragging, `snap_near`
says what a release would land on, for the hint in the camera strip.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from vectra3d import config
from vectra3d.core.spherical import (
    FULL_TURN,
    normalize_phi,
    to_components,
    to_spherical,
)
from vectra3d.core.vector_math import magnitude, unit_vector
from vectra3d.gestures.hand_metrics import Point, distance

# A direction or point in the 3D world.
Triple = tuple[float, float, float]


def _cross(a: Triple, b: Triple) -> Triple:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def screen_axes(direction: Triple, up: Triple) -> tuple[Triple, Triple] | None:
    """The world directions of the screen's right and up, as unit vectors.

    `direction` is where the camera looks and `up` its view-up vector. The
    view-up is **not** the screen's up: PyVista keeps whatever it was set to,
    so a camera looking down at the scene with z up still reports (0, 0, 1),
    tilted away from the screen. Using it as is would tip every created
    vector towards or away from the student. So right is worked out first,
    square to both, and the screen's up is taken square to right and the
    view direction.

    None only if the camera looks straight along its own up, which leaves no
    screen to speak of.
    """
    right = unit_vector(_cross(direction, up))
    if right is None:
        return None
    screen_up = unit_vector(_cross(right, direction))
    if screen_up is None:
        return None
    return right, screen_up


def head_index(start_points: tuple[Point, Point], points: tuple[Point, Point]) -> int:
    """Which of the two hands is the head of a vector being created (6.2).

    The head is at the hand that has moved further from where its pinch
    began - the "pulling" hand - so a student can pull either way with either
    hand. If the two have moved within the equal-movement margin of each
    other, neither is clearly leading and the head is at the hand on the
    right of the screen. Re-evaluated every frame, so it settles as soon as
    one hand clearly leads.
    """
    moved = [distance(start, now) for start, now in zip(start_points, points)]
    if abs(moved[0] - moved[1]) <= config.EQUAL_MOVEMENT_MARGIN * max(moved):
        return 0 if points[0][0] > points[1][0] else 1
    return 0 if moved[0] > moved[1] else 1


def stretch(
    start_points: tuple[Point, Point],
    start_scale: float,
    points: tuple[Point, Point],
    scale: float,
    sensitivity: float,
) -> float | None:
    """How much length the hands' stretch adds, in scene units (6.2, 6.3).

    (current distance - starting distance) / full stretch * sensitivity, with
    each distance in hand-scale units of its own moment, so leaning in
    mid-gesture does not by itself change the answer. Negative when the hands
    have come closer than they started, which is how a resize shrinks.

    None if either hand scale is zero, when no distance can be measured.
    """
    if start_scale <= 0 or scale <= 0:
        return None
    start_hs = distance(*start_points) / start_scale
    now_hs = distance(*points) / scale
    return (now_hs - start_hs) / config.FULL_STRETCH_HS * sensitivity


def create_components(
    start_points: tuple[Point, Point],
    start_scale: float,
    points: tuple[Point, Point],
    scale: float,
    axes: tuple[Triple, Triple],
    sensitivity: float,
) -> Triple | None:
    """The vector two pinching hands are drawing (6.2).

    It points along the line from the tail hand to the head hand, carried
    into the world by the screen's `axes` (right, up), so it starts parallel
    to the screen; depth is added by steering afterwards. Its length is the
    stretch, never below zero: bringing the hands closer than they started
    gives nothing, not a vector pointing backwards.

    The zero vector while the hands have not moved apart, or lie exactly on
    top of each other. None if nothing can be measured this frame.
    """
    added = stretch(start_points, start_scale, points, scale, sensitivity)
    if added is None:
        return None
    length = max(0.0, added)

    head = head_index(start_points, points)
    head_point, tail_point = points[head], points[1 - head]
    across = head_point[0] - tail_point[0]
    # Picture y grows downward; the screen's up is the other way.
    upward = tail_point[1] - head_point[1]
    right, screen_up = axes
    along = unit_vector(
        tuple(across * r + upward * u for r, u in zip(right, screen_up))
    )
    if along is None or length == 0.0:
        return (0.0, 0.0, 0.0)
    return tuple(length * value for value in along)


def resize_components(
    original: Triple,
    start_points: tuple[Point, Point],
    start_scale: float,
    points: tuple[Point, Point],
    scale: float,
    sensitivity: float,
) -> Triple | None:
    """A vector resized by two pinching hands (6.3).

    Its direction stays exactly that of `original`, the vector as it was when
    the resize began. Its length is the original length plus the stretch, at
    the same rate as creating, and never below the minimum magnitude, however
    far the hands close.

    None if nothing can be measured this frame, or if `original` is the zero
    vector, which has no direction to keep.
    """
    along = unit_vector(original)
    added = stretch(start_points, start_scale, points, scale, sensitivity)
    if along is None or added is None:
        return None
    length = max(config.MIN_MAGNITUDE, magnitude(original) + added)
    return tuple(length * value for value in along)




def hand_movement(before: Point, after: Point, scale: float) -> tuple[float, float] | None:
    """How far the steering hand moved between two frames, in hs (6.4).

    (right, up): picture y grows downward, so it is flipped. Measured in
    the hand scale of the newer frame, so leaning in mid-drag does not by
    itself turn the vector faster. None if that scale is zero.
    """
    if scale <= 0:
        return None
    return ((after[0] - before[0]) / scale, (before[1] - after[1]) / scale)


@dataclass(frozen=True)
class Heading:
    """Which way a steered vector points, as its two angles (2.3), in °.

    `theta` from +z, 0 to 180; `phi` round the floor from +x towards +y,
    0 to 360. Steering changes these directly (6.4), so hand up and down
    always mean towards +z and -z, whatever the view.
    """

    theta: float
    phi: float


def heading_of(components: Triple) -> Heading | None:
    """The angles of a vector, or None for the zero vector."""
    spherical = to_spherical(components)
    if spherical is None:
        return None
    _, theta, phi = spherical
    return Heading(theta, phi)


@dataclass(frozen=True)
class Meridian:
    """A steered direction as a place on the vertical circle through z (6.4).

    The circle stands at `phi`, and `tilt` is how far round it the head is
    from +z, in °, from -180 to 180: positive on the `phi` side, negative
    once it has gone over the top (or under the bottom) onto the other side.
    Theta alone stops at 0 and 180; the tilt does not, so dragging up keeps
    turning the vector the same way, over the top and down the far side.
    """

    tilt: float
    phi: float

    @property
    def heading(self) -> Heading:
        if self.tilt >= 0.0:
            return Heading(self.tilt, self.phi)
        return Heading(-self.tilt, normalize_phi(self.phi + 180.0))


def _wrap(angle: float) -> float:
    """An angle in °, into -180 to 180."""
    return (angle + 180.0) % 360.0 - 180.0


def meridian_of(heading: Heading) -> Meridian:
    return Meridian(heading.theta, heading.phi)


def drag_meridian(meridian: Meridian, movement: tuple[float, float]) -> Meridian:
    """Where the hand's movement, in hs, takes the vector (6.4).

    Up turns the head towards +z and down towards -z, by the steering rate
    per hs, round its vertical circle with no stop: past a pole it carries
    on down the other side. Sideways turns that circle round z, always the
    same way: right raises phi, anticlockwise seen from above, so the side
    of the turntable nearest a viewer above the floor follows the hand -
    wherever the vector points, and whatever it has done since the grab.
    """
    across, upward = movement
    rate = config.STEER_DEG_PER_HS
    return Meridian(
        _wrap(meridian.tilt - upward * rate),
        normalize_phi(meridian.phi + across * rate),
    )


_POLES = (0.0, 180.0)


def at_pole(heading: Heading) -> bool:
    """Whether a heading is exactly on the z axis, where phi means nothing."""
    return heading.theta in _POLES


def _flat(direction: Triple) -> Triple | None:
    """A direction's shadow on the floor, as a unit vector, or None."""
    return unit_vector((direction[0], direction[1], 0.0))


def leave_pole(
    heading: Heading, movement: tuple[float, float], axes: tuple[Triple, Triple]
) -> Heading:
    """Dragging at the z axis: the head leaves it the way the hand moves (6.4).

    `heading` is on a pole. The movement is turned into a direction on the
    floor - the screen's right and up, flattened - and the head is tipped
    from the pole towards that direction, by the steering rate per hs. The
    part of the movement pointing further into the pole (up at +z, down at
    -z) is dropped. The screen's right is always level; its up lies flat
    only when the view is level, and then the head has nowhere up or down
    on screen to go but towards or away from the viewer, which is the
    direction up would take anyway.
    """
    right, screen_up = axes
    across, upward = movement
    north = heading.theta < 90.0
    if (upward > 0.0) == north:
        upward = 0.0
    floor_right, floor_up = _flat(right), _flat(screen_up)
    if floor_right is None:
        return heading
    floor_up = floor_up or _cross((0.0, 0.0, 1.0), floor_right)
    toward = unit_vector(
        tuple(across * r + upward * u for r, u in zip(floor_right, floor_up))
    )
    if toward is None:
        return heading
    angle = math.radians(config.STEER_DEG_PER_HS * math.hypot(across, upward))
    pole = (0.0, 0.0, 1.0 if north else -1.0)
    # Rodrigues' rotation about the axis square to the pole and the target
    # direction, which turns the head from the pole straight towards it.
    axis = unit_vector(_cross(pole, toward))
    current = to_components(1.0, heading.theta, heading.phi)
    cos, sin = math.cos(angle), math.sin(angle)
    along = sum(k * v for k, v in zip(axis, current))
    turned = tuple(
        v * cos + c * sin + k * along * (1.0 - cos)
        for v, c, k in zip(current, _cross(axis, current), axis)
    )
    return heading_of(turned) or heading


THETA_SNAPS = (0.0, 90.0, 180.0)
PHI_SNAPS = (0.0, 90.0, 180.0, 270.0)
_PHI_AXES = {0.0: "+x", 90.0: "+y", 180.0: "-x", 270.0: "-y"}


def _near(value: float, stops: tuple[float, ...], turn: float | None) -> float | None:
    """The snap value an angle is within reach of, or None.

    Round the circle for phi, so 356° is in reach of 0°. The snap values
    are 90° apart, so at most one can be in reach.
    """
    for stop in stops:
        gap = abs(value - stop)
        if turn is not None:
            gap = min(gap, turn - gap)
        if gap <= config.SNAP_DEG:
            return stop
    return None


@dataclass(frozen=True)
class Snap:
    """The angles a release would snap to, each None if free (6.5).

    Never both None: no snap at all is None rather than an empty Snap.
    """

    theta: float | None
    phi: float | None

    @property
    def label(self) -> str:
        """What the vector would lie on, for the camera strip."""
        if self.theta in _POLES:
            return "+z axis" if self.theta == 0.0 else "-z axis"
        if self.theta is not None and self.phi is not None:
            return f"{_PHI_AXES[self.phi]} axis"
        if self.theta is not None:
            return "XY plane"
        return "XZ plane" if self.phi in (0.0, 180.0) else "YZ plane"


def snap_near(heading: Heading) -> Snap | None:
    """What releasing at this heading would snap to (6.5), or None."""
    theta = _near(heading.theta, THETA_SNAPS, None)
    # On the z axis phi means nothing, so it is never snapped there.
    phi = None if theta in _POLES else _near(heading.phi, PHI_SNAPS, FULL_TURN)
    return None if theta is None and phi is None else Snap(theta, phi)


def snapped(heading: Heading, snap: Snap | None) -> Heading:
    """The heading with each snapped angle replaced by its snap value."""
    if snap is None:
        return heading
    return Heading(
        heading.theta if snap.theta is None else snap.theta,
        heading.phi if snap.phi is None else snap.phi,
    )


def heading_components(heading: Heading, length: float) -> Triple:
    """The vector for a heading, at `length`, exact on axes and planes.

    `sin` and `cos` of a right angle are not exact in floating point -
    cos 90° is 6e-17 - so a vector snapped into the floor would keep a
    z of 6e-17. Each component an angle on a snap value makes zero is set
    to zero.
    """
    x, y, z = to_components(length, heading.theta, heading.phi)
    if heading.theta in _POLES:
        x = y = 0.0
    elif heading.theta == 90.0:
        z = 0.0
    if heading.phi in (0.0, 180.0):
        y = 0.0
    elif heading.phi in (90.0, 270.0):
        x = 0.0
    return (x, y, z)


def is_long_enough(components: Triple) -> bool:
    """Whether a vector made by hand is kept on release (6.2 step 4)."""
    return magnitude(components) >= config.MIN_MAGNITUDE

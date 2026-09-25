"""Turning hand positions into vectors (`interaction-spec.md` section 6).

The state machine says what the hands are doing; this works out what that
means for a vector. Pure maths on plain tuples - no camera, no Qt, no
PyVista - so every rule is tested with hand-calculated values.

**Screen-relative directions (6.1).** A hand moving right in the mirrored
picture means the camera's right in the 3D world, and a hand moving up means
the camera's up, whichever way the view has been turned. Picture y grows
downward, so it is flipped.

**Snapping (6.5)** works on the *steered* direction - where the joystick has
turned the vector, before snapping - rather than on the vector as shown.
Turned from the snapped vector, each frame would move it a few degrees off
the axis, it would snap straight back, and it could never get far enough
away to leave.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from vectra3d import config
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


def deflection(anchor: Point, point: Point, scale: float) -> tuple[float, float] | None:
    """How far the steering hand is from its anchor, in hs, on screen (6.4).

    (right, up): picture y grows downward, so it is flipped. Measured in the
    hand scale at the anchor, so the joystick's size stays fixed for the
    whole gesture. None if that scale is zero.
    """
    if scale <= 0:
        return None
    return ((point[0] - anchor[0]) / scale, (anchor[1] - point[1]) / scale)


def steer_speed(deflection_hs: float) -> float:
    """How fast a joystick this far from its anchor turns the vector, in °/s.

    Nothing inside the dead zone, so a hand held still with a little shake
    moves nothing. Beyond it the speed rises in a straight line from zero at
    the dead zone's edge - so there is no jump when the hand crosses it - to
    the maximum at the full-speed deflection, and stays there.
    """
    beyond = deflection_hs - config.STEER_DEAD_ZONE_HS
    if beyond <= 0:
        return 0.0
    span = config.STEER_MAX_SPEED_HS - config.STEER_DEAD_ZONE_HS
    return config.STEER_MAX_SPEED_DEG_PER_S * min(1.0, beyond / span)


def _dot(a: Triple, b: Triple) -> float:
    return sum(x * y for x, y in zip(a, b))


def turn_axes(
    axes: tuple[Triple, Triple], locks: tuple[Triple, ...] = ()
) -> tuple[Triple, Triple]:
    """What the joystick turns the vector about: (for sideways, for up/down).

    Normally the screen's up and minus its right (see `steer_components`).

    **Snap lock (6.5).** `locks` are the normals of the planes a snapped
    vector lies in: one for a plane, two for an axis, which lies in two.
    Each replaces the screen axis nearest to it, so the hand direction that
    used it turns the vector *within* that plane, whichever way the view is
    turned. Without this, a sideways push in a view looking down at the floor
    turns the vector about a tilted axis, and it dips out of the XY plane as
    it goes - found with real hands at G5.6. On a plane, the other hand
    direction still tilts the vector out, which is how it leaves; on an axis,
    each hand direction leaves along one of its two planes.

    Which screen axis a normal replaces: for a plane, the one it lies closer
    to - sideways spins the floor seen from above, up/down spins the YZ
    plane seen edge-on from the front. For an axis, the normal closer to the
    screen's up takes sideways and the other takes up/down.

    Each normal is signed to point the way the screen axis it replaces does,
    which keeps the globe-style sense. A normal square to that screen axis
    is taken towards the student instead.
    """
    right, screen_up = axes
    sideways, upward = screen_up, tuple(-value for value in right)
    towards_student = _cross(right, screen_up)

    def signed(normal: Triple, like: Triple) -> Triple:
        lean = _dot(normal, like) or _dot(normal, towards_student)
        return tuple(value if lean >= 0 else -value for value in normal)

    if len(locks) == 1:
        (normal,) = locks
        if abs(_dot(normal, screen_up)) >= abs(_dot(normal, right)):
            return signed(normal, sideways), upward
        return sideways, signed(normal, upward)
    if len(locks) == 2:
        first, second = sorted(locks, key=lambda n: -abs(_dot(n, screen_up)))
        return signed(first, sideways), signed(second, upward)
    return sideways, upward


def steer_components(
    current: Triple,
    length: float,
    push: tuple[float, float],
    seconds: float,
    axes: tuple[Triple, Triple],
    locks: tuple[Triple, ...] = (),
) -> Triple:
    """The vector after `seconds` of steering with the joystick at `push` (6.4).

    Horizontal deflection turns it about the screen's up, vertical about the
    screen's right, combined into one turn for a diagonal push. The sense is
    **globe-style**: the side of the vector nearest the viewer moves the way
    the hand moves, the usual convention for turning things in 3D. A vector
    pointing at the student swings with the hand; one pointing into the
    screen swings the other way; one lying flat on the screen tips into or
    out of it - which is how steering adds the depth a created vector lacks.

    The turn is exact for the time step (Rodrigues' rotation formula), and
    the result is scaled back to `length` - the magnitude it had when the
    steering began - so rounding cannot make the vector creep longer or
    shorter over thousands of frames (6.4 step 6).
    """
    across, upward = push
    speed = steer_speed(math.hypot(across, upward))
    if speed == 0.0 or seconds <= 0.0:
        return current

    # The near side of the vector points along -view. Turning about the
    # screen's up moves -view towards right (up x -view = right), and about
    # -right moves it towards up (-right x -view = up), so turning about
    # (across * up - upward * right) moves the near side by (across, upward).
    # `turn_axes` swaps them for plane normals while the vector is snapped.
    sideways, vertical = turn_axes(axes, locks)
    axis = unit_vector(
        tuple(across * s + upward * v for s, v in zip(sideways, vertical))
    )
    if axis is None:
        return current

    angle = math.radians(speed * seconds)
    cos, sin = math.cos(angle), math.sin(angle)
    along = sum(k * v for k, v in zip(axis, current))
    turned = tuple(
        v * cos + c * sin + k * along * (1.0 - cos)
        for v, c, k in zip(current, _cross(axis, current), axis)
    )
    direction = unit_vector(turned)
    if direction is None:
        return current
    return tuple(length * value for value in direction)


_AXIS_NAMES = ("x", "y", "z")
# A coordinate plane is named by the two axes in it; its normal is the third.
_PLANE_NAMES = ("YZ", "XZ", "XY")


@dataclass(frozen=True)
class SnapTarget:
    """An axis or coordinate plane a steered vector can snap onto (6.5).

    `index` is the axis (0, 1, 2 for x, y, z), or for a plane the axis
    square to it. `sign` is +1 or -1 along an axis, and 0 for a plane, which
    has no direction along it.
    """

    index: int
    sign: int = 0

    @property
    def is_plane(self) -> bool:
        return self.sign == 0

    @property
    def locks(self) -> tuple[Triple, ...]:
        """The normals of the planes a vector snapped here lies in.

        One for a plane; two for an axis, which lies in the two planes
        square to the other axes. Steering turns it within these.
        """
        others = (self.index,) if self.is_plane else tuple(
            index for index in range(3) if index != self.index
        )
        return tuple(
            tuple(1.0 if axis == other else 0.0 for axis in range(3)) for other in others
        )

    @property
    def label(self) -> str:
        if self.is_plane:
            return f"{_PLANE_NAMES[self.index]} plane"
        return f"{'+' if self.sign > 0 else '-'}{_AXIS_NAMES[self.index]} axis"


def angle_from(direction: Triple, target: SnapTarget) -> float:
    """How far a direction is from an axis or from lying in a plane, in °.

    The cosine or sine is clamped, since a component over its own magnitude
    can land one step past 1 and `math.acos` would raise (see G2.1).
    """
    along = unit_vector(direction)
    if along is None:
        return 90.0
    share = along[target.index]
    if target.is_plane:
        return math.degrees(math.asin(min(1.0, abs(share))))
    return math.degrees(math.acos(max(-1.0, min(1.0, target.sign * share))))


def exact_target(components: Triple) -> SnapTarget | None:
    """The axis, or failing that the plane, a vector lies exactly on.

    A vector already on one when steering begins counts as snapped to it
    from the start, so it needs the full release angle to leave and does not
    flash as if it had just arrived.
    """
    zeros = [index for index, value in enumerate(components) if value == 0.0]
    if len(zeros) == 2:
        index = 3 - sum(zeros)
        return SnapTarget(index, 1 if components[index] > 0 else -1)
    if len(zeros) == 1:
        return SnapTarget(zeros[0])
    return None


def snap_target(steered: Triple, current: SnapTarget | None) -> SnapTarget | None:
    """What a steered direction snaps onto this frame (6.5).

    An axis within the snap-in angle always wins, even over a plane the
    vector is sliding along. Otherwise the current target holds until the
    steering is past the release angle from it, so the vector does not
    flicker at the edge. Failing both, the nearest plane within the snap-in
    angle, or nothing.

    Only one axis can be within 5° of any direction, and the nearest is along
    the largest component; the nearest plane is square to the smallest.
    """
    sizes = [abs(value) for value in steered]
    widest = sizes.index(max(sizes))
    axis = SnapTarget(widest, 1 if steered[widest] > 0 else -1)
    if angle_from(steered, axis) <= config.SNAP_IN_DEG:
        return axis
    if current is not None and angle_from(steered, current) <= config.SNAP_RELEASE_DEG:
        return current
    plane = SnapTarget(sizes.index(min(sizes)))
    if angle_from(steered, plane) <= config.SNAP_IN_DEG:
        return plane
    return None


def snapped_components(steered: Triple, length: float, target: SnapTarget | None) -> Triple:
    """The vector as shown: `steered` moved exactly onto `target`, at `length`.

    Onto an axis it is that axis at full length. Into a plane, the part
    sticking out of it is dropped and the rest scaled back up, so it keeps
    its heading within the plane. With no target it is `steered` unchanged.
    """
    if target is None:
        return steered
    if not target.is_plane:
        return tuple(
            float(target.sign) * length if index == target.index else 0.0
            for index in range(3)
        )
    flat = unit_vector(
        tuple(0.0 if index == target.index else value for index, value in enumerate(steered))
    )
    if flat is None:
        return steered
    return tuple(length * value for value in flat)


def is_long_enough(components: Triple) -> bool:
    """Whether a vector made by hand is kept on release (6.2 step 4)."""
    return magnitude(components) >= config.MIN_MAGNITUDE

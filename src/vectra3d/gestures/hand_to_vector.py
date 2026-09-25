"""Turning hand positions into vectors (`interaction-spec.md` section 6).

The state machine says what the hands are doing; this works out what that
means for a vector. Pure maths on plain tuples - no camera, no Qt, no
PyVista - so every rule is tested with hand-calculated values.

**Screen-relative directions (6.1).** A hand moving right in the mirrored
picture means the camera's right in the 3D world, and a hand moving up means
the camera's up, whichever way the view has been turned. Picture y grows
downward, so it is flipped.
"""

from __future__ import annotations

import math

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


def steer_components(
    current: Triple,
    length: float,
    push: tuple[float, float],
    seconds: float,
    axes: tuple[Triple, Triple],
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

    right, screen_up = axes
    # The near side of the vector points along -view. Turning about the
    # screen's up moves -view towards right (up x -view = right), and about
    # -right moves it towards up (-right x -view = up), so turning about
    # (across * up - upward * right) moves the near side by (across, upward).
    axis = unit_vector(
        tuple(across * u - upward * r for u, r in zip(screen_up, right))
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


def is_long_enough(components: Triple) -> bool:
    """Whether a vector made by hand is kept on release (6.2 step 4)."""
    return magnitude(components) >= config.MIN_MAGNITUDE

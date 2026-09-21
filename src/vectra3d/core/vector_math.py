"""How long a vector is, and which way it points.

The three quantities from `interaction-spec.md` section 2.4, which the info
panel shows for every vector and, from G3, for every operation result:

- the **magnitude** |v|,
- the **direction angles** alpha, beta and gamma, the angles the vector makes
  with the +x, +y and +z axes,
- the **unit vector** v / |v|, one unit long and pointing the same way.

These are not the spherical theta and phi in `spherical.py`. Those two angles
locate a direction; these three describe how the vector leans towards each
axis in turn, and they satisfy cos^2 a + cos^2 b + cos^2 c = 1.

**The zero vector has no direction**, so `direction_angles` and `unit_vector`
return `None` for it rather than a number. Section 2.4 says to display an em
dash in that case, and `None` is what makes the caller deal with it: a nan
would be silently carried into whatever it touched next.

Magnitude uses `math.hypot` rather than `numpy.linalg.norm`, against the
general rule in `architecture.md` section 1 that NumPy does the vector maths.
These are three scalars, not an array, and `norm` squares them before taking a
root, so it overflows to infinity for components around 1e154 and underflows
to zero for components around 1e-200 - both from input the app accepts as
finite. `hypot` is correctly rounded and does neither. The angles follow it
into `math` for consistency; NumPy remains the rule wherever the data is
actually array-shaped.
"""

from __future__ import annotations

import math

# A triple of x, y, z. `state.models.Point` is the same shape, but `core` sits
# below `state` and may not import from it (`architecture.md` section 2).
Triple = tuple[float, float, float]


def magnitude(components: Triple) -> float:
    """The length of the vector, |v| = sqrt(x^2 + y^2 + z^2)."""
    return math.hypot(*components)


def direction_angles(components: Triple) -> Triple | None:
    """The angles with the +x, +y and +z axes, in degrees, or `None`.

    alpha = arccos(x / |v|), and likewise for beta and gamma. Each comes back
    between 0 and 180 degrees: 0 when the vector points along that axis, 180
    when it points the opposite way, 90 when it is square to it.

    Returns `None` for the zero vector, which has no direction.
    """
    length = magnitude(components)
    if length == 0.0:
        return None

    return (
        _angle_with_axis(components[0], length),
        _angle_with_axis(components[1], length),
        _angle_with_axis(components[2], length),
    )


def unit_vector(components: Triple) -> Triple | None:
    """The vector scaled to length 1, v / |v|, or `None`.

    Returns `None` for the zero vector, which has no direction to keep.
    """
    length = magnitude(components)
    if length == 0.0:
        return None

    return (
        components[0] / length,
        components[1] / length,
        components[2] / length,
    )


def _angle_with_axis(component: float, length: float) -> float:
    """One direction angle in degrees, from a component and the magnitude.

    The ratio is clamped before `acos` sees it. For a vector lying on an axis
    the true cosine is exactly 1 or -1, which is the very edge of the domain,
    and a ratio a single step beyond it makes `acos` raise `ValueError` - a
    crash, on the most ordinary vector a student can type.
    """
    ratio = min(1.0, max(-1.0, component / length))
    return math.degrees(math.acos(ratio))

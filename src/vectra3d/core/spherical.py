"""Spherical coordinates: magnitude and two angles, to and from components.

The physics convention from `interaction-spec.md` section 2.3, which is the
one most first-year courses use:

- **r** is the magnitude, greater than 0.
- **theta** is measured from the +z axis, 0 to 180 degrees.
- **phi** is measured in the XY plane from +x toward +y, counterclockwise seen
  from above. Any value is normalized into 0 to 360 degrees.

Along the z axis (theta of 0 or 180 degrees) phi means nothing, because there
is no direction in the XY plane left to point in. Nothing here objects to a
phi in that case; it simply has no effect on the answer.
"""

from __future__ import annotations

import math

import numpy as np

from vectra3d.core.vector_math import direction_angles, magnitude

THETA_MIN = 0.0
THETA_MAX = 180.0
FULL_TURN = 360.0


def normalize_phi(phi_deg: float) -> float:
    """Bring any angle into 0 to 360 degrees: 370 becomes 10, -90 becomes 270."""
    return float(phi_deg % FULL_TURN)


def to_components(
    r: float, theta_deg: float, phi_deg: float
) -> tuple[float, float, float]:
    """Convert magnitude and angles into (x, y, z).

        x = r sin(theta) cos(phi)
        y = r sin(theta) sin(phi)
        z = r cos(theta)

    Full precision is kept and nothing is rounded or snapped, as
    `interaction-spec.md` section 2.2 requires. A vector typed as
    r=1, theta=90, phi=90 therefore stores x as 6.1e-17 rather than zero;
    that is the true value of cos(90 degrees) in floating point, and it
    displays as 0.00 once the display rounding in `core/formatting.py`
    is applied.
    """
    theta = np.radians(theta_deg)
    phi = np.radians(normalize_phi(phi_deg))

    return (
        float(r * np.sin(theta) * np.cos(phi)),
        float(r * np.sin(theta) * np.sin(phi)),
        float(r * np.cos(theta)),
    )


def to_spherical(components: tuple[float, float, float]) -> tuple[float, float, float] | None:
    """Convert (x, y, z) back into magnitude and angles: the inverse of `to_components`.

        r     = sqrt(x^2 + y^2 + z^2)
        theta = arccos(z / r)
        phi   = atan2(y, x), brought into 0 to 360 degrees

    Returns `None` for the zero vector, which has no direction at all, the
    same answer `vector_math.direction_angles` gives and for the same reason:
    a caller has to deal with it before it can display anything.

    Theta is not computed here. The angle from the +z axis *is* the direction
    angle gamma, so it comes from `vector_math.direction_angles`, which
    already clamps the ratio before `acos` sees it - without that, a vector
    lying on the z axis can raise `ValueError` one floating-point step outside
    the domain.

    Along the z axis phi is undefined, since there is no direction left in the
    XY plane to measure. `atan2(0.0, 0.0)` is defined as 0.0 rather than an
    error, so that is what comes back; section 2.3 says a typed phi is
    irrelevant there, and the panel says so next to the field.
    """
    r = magnitude(components)
    angles = direction_angles(components)
    if angles is None:
        return None

    x, y, _ = components
    phi = normalize_phi(math.degrees(math.atan2(y, x)))
    return (r, angles[2], phi)

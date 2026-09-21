"""Magnitude and angles to components and back (`interaction-spec.md` section 2.3).

Expected values are worked out by hand, from
x = r sin(theta) cos(phi), y = r sin(theta) sin(phi), z = r cos(theta),
and for the inverse from r = |v|, theta = arccos(z / r), phi = atan2(y, x).
"""

from __future__ import annotations

import math

import pytest

from vectra3d.core.spherical import normalize_phi, to_components, to_spherical
from vectra3d.core.vector_math import direction_angles

# Floating point never lands exactly on zero for these angles, so comparisons
# allow the last few digits to differ.
TOL = 1e-12


def close(actual: tuple[float, float, float], expected: tuple[float, float, float]):
    assert actual == pytest.approx(expected, abs=TOL)


# --- Along each axis ---


def test_along_positive_x() -> None:
    # theta 90 puts it in the XY plane; phi 0 points it along +x.
    close(to_components(1.0, 90.0, 0.0), (1.0, 0.0, 0.0))


def test_along_positive_y() -> None:
    close(to_components(1.0, 90.0, 90.0), (0.0, 1.0, 0.0))


def test_along_negative_x() -> None:
    close(to_components(5.0, 90.0, 180.0), (-5.0, 0.0, 0.0))


def test_along_negative_y() -> None:
    close(to_components(2.0, 90.0, 270.0), (0.0, -2.0, 0.0))


def test_straight_up() -> None:
    close(to_components(3.0, 0.0, 0.0), (0.0, 0.0, 3.0))


def test_straight_down() -> None:
    close(to_components(3.0, 180.0, 0.0), (0.0, 0.0, -3.0))


def test_phi_does_not_matter_along_the_z_axis() -> None:
    # With no part in the XY plane there is no direction for phi to choose.
    close(to_components(3.0, 0.0, 123.0), (0.0, 0.0, 3.0))
    close(to_components(3.0, 180.0, 45.0), (0.0, 0.0, -3.0))


# --- A worked example ---


def test_a_hand_calculated_example() -> None:
    # r=2, theta=60, phi=30:
    #   x = 2 * sin60 * cos30 = 2 * (sqrt3/2) * (sqrt3/2) = 1.5
    #   y = 2 * sin60 * sin30 = 2 * (sqrt3/2) * 0.5       = sqrt3/2
    #   z = 2 * cos60         = 2 * 0.5                   = 1
    close(to_components(2.0, 60.0, 30.0), (1.5, math.sqrt(3) / 2, 1.0))


def test_the_magnitude_is_preserved() -> None:
    x, y, z = to_components(7.0, 35.0, 200.0)
    assert math.sqrt(x * x + y * y + z * z) == pytest.approx(7.0)


# --- Normalizing phi ---


@pytest.mark.parametrize(
    ("given", "expected"),
    [(0.0, 0.0), (10.0, 10.0), (370.0, 10.0), (-90.0, 270.0), (720.0, 0.0)],
)
def test_phi_is_brought_into_one_turn(given: float, expected: float) -> None:
    assert normalize_phi(given) == pytest.approx(expected)


def test_a_phi_past_one_turn_gives_the_same_vector() -> None:
    close(to_components(2.0, 60.0, 390.0), to_components(2.0, 60.0, 30.0))


def test_a_negative_phi_gives_the_same_vector() -> None:
    close(to_components(2.0, 60.0, -90.0), to_components(2.0, 60.0, 270.0))


# --- Components back to magnitude and angles ---


def test_the_magnitude_comes_back() -> None:
    r, _, _ = to_spherical((3.0, 4.0, 12.0))
    assert r == pytest.approx(13.0)


def test_a_vector_up_the_z_axis_has_theta_zero() -> None:
    # Straight up: no tilt away from +z at all.
    r, theta, _ = to_spherical((0.0, 0.0, 5.0))
    assert (r, theta) == pytest.approx((5.0, 0.0))


def test_a_vector_down_the_z_axis_has_theta_180() -> None:
    r, theta, _ = to_spherical((0.0, 0.0, -5.0))
    assert (r, theta) == pytest.approx((5.0, 180.0))


def test_a_vector_in_the_xy_plane_has_theta_90() -> None:
    _, theta, _ = to_spherical((2.0, 2.0, 0.0))
    assert theta == pytest.approx(90.0)


@pytest.mark.parametrize(
    ("components", "expected_phi"),
    [
        ((1.0, 0.0, 0.0), 0.0),  # +x
        ((0.0, 1.0, 0.0), 90.0),  # +y
        ((-1.0, 0.0, 0.0), 180.0),  # -x
        ((0.0, -1.0, 0.0), 270.0),  # -y, the case atan2 gives as -90
        ((1.0, 1.0, 0.0), 45.0),  # first quadrant
        ((-1.0, 1.0, 0.0), 135.0),  # second
        ((-1.0, -1.0, 0.0), 225.0),  # third
        ((1.0, -1.0, 0.0), 315.0),  # fourth
    ],
)
def test_phi_covers_the_whole_turn(
    components: tuple[float, float, float], expected_phi: float
) -> None:
    _, _, phi = to_spherical(components)
    assert phi == pytest.approx(expected_phi)


def test_phi_is_never_negative() -> None:
    # atan2 answers in -180 to 180; section 2.3 asks for 0 to 360.
    for components in ((1.0, -1.0, 0.0), (0.0, -3.0, 4.0), (-2.0, -2.0, -2.0)):
        _, _, phi = to_spherical(components)
        assert 0.0 <= phi < 360.0


def test_phi_on_the_z_axis_is_zero_rather_than_an_error() -> None:
    # Undefined there (section 2.3), and the panel says so; atan2(0, 0) is
    # defined as 0.0, so nothing raises and the field has a value to hold.
    assert to_spherical((0.0, 0.0, 4.0))[2] == 0.0


def test_the_zero_vector_has_no_spherical_form() -> None:
    assert to_spherical((0.0, 0.0, 0.0)) is None


def test_theta_is_the_direction_angle_gamma() -> None:
    # Two names for the same angle: theta is measured from +z, and so is gamma.
    components = (1.0, -2.0, 3.0)
    assert to_spherical(components)[1] == pytest.approx(direction_angles(components)[2])


# --- Round trips ---


@pytest.mark.parametrize(
    "components",
    [
        (3.0, 4.0, 0.0),
        (1.0, 1.0, 1.0),
        (-2.0, 5.0, -1.0),
        (0.0, 0.0, 7.0),
        (0.0, 0.0, -7.0),
        (-6.0, -3.0, 2.0),
    ],
)
def test_components_survive_a_round_trip(
    components: tuple[float, float, float]
) -> None:
    r, theta, phi = to_spherical(components)
    close(to_components(r, theta, phi), components)


@pytest.mark.parametrize(
    ("r", "theta", "phi"),
    [(5.0, 53.13010235415598, 90.0), (1.0, 90.0, 0.0), (2.5, 120.0, 200.0)],
)
def test_angles_survive_a_round_trip(r: float, theta: float, phi: float) -> None:
    assert to_spherical(to_components(r, theta, phi)) == pytest.approx(
        (r, theta, phi), abs=1e-9
    )

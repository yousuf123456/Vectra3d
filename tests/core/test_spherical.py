"""Magnitude and angles to components (`interaction-spec.md` section 2.3).

Expected values are worked out by hand, from
x = r sin(theta) cos(phi), y = r sin(theta) sin(phi), z = r cos(theta).
"""

from __future__ import annotations

import math

import pytest

from vectra3d.core.spherical import normalize_phi, to_components

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

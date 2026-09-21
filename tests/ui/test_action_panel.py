"""Reading and checking what is typed into the create form (F-04).

Only the parsing is tested here, not the widgets: these are the rules that
decide whether a vector is created, and they are what F-04's criteria are
about. No window is opened.
"""

from __future__ import annotations

import math

import pytest

from vectra3d.ui.action_panel import parse_angles, parse_components, parse_number


# --- One field at a time ---


def test_a_plain_number_is_read() -> None:
    assert parse_number("3.5", "x") == (3.5, None)


def test_surrounding_spaces_are_ignored() -> None:
    assert parse_number("  -2 ", "x") == (-2.0, None)


def test_an_empty_field_says_which_one() -> None:
    value, error = parse_number("   ", "y")
    assert value is None
    assert error == "Enter a value for y."


def test_something_that_is_not_a_number_is_refused() -> None:
    value, error = parse_number("abc", "z")
    assert value is None
    assert "must be a number" in error


def test_a_comma_decimal_is_refused_with_advice() -> None:
    # A real typo for anyone taught to write 3,5. The message has to say what
    # to do instead, because the field itself accepts the keystroke.
    value, error = parse_number("3,5", "x")
    assert value is None
    assert "dot for decimals" in error


# --- The components form ---


def test_valid_components_are_read() -> None:
    assert parse_components("1", "2", "3").components == (1.0, 2.0, 3.0)


def test_negative_components_are_fine() -> None:
    assert parse_components("-1", "0", "2.5").components == (-1.0, 0.0, 2.5)


def test_the_zero_vector_is_refused() -> None:
    parsed = parse_components("0", "0", "0")
    assert parsed.components is None
    assert "needs a direction" in parsed.error


def test_one_bad_field_stops_the_whole_form() -> None:
    parsed = parse_components("1", "oops", "3")
    assert parsed.components is None
    assert parsed.error.startswith("y")


# --- The magnitude and angles form ---


def test_valid_angles_are_converted() -> None:
    parsed = parse_angles("2", "60", "30")
    assert parsed.components == pytest.approx((1.5, math.sqrt(3) / 2, 1.0))


def test_a_magnitude_of_zero_is_refused() -> None:
    # A zero magnitude is the zero vector by another name, and section 2.3
    # requires r greater than 0.
    parsed = parse_angles("0", "60", "30")
    assert parsed.components is None
    assert "greater than 0" in parsed.error


def test_a_negative_magnitude_is_refused() -> None:
    parsed = parse_angles("-3", "60", "30")
    assert parsed.components is None
    assert "greater than 0" in parsed.error


@pytest.mark.parametrize("theta", ["-1", "181", "360"])
def test_theta_outside_its_range_is_refused(theta: str) -> None:
    parsed = parse_angles("2", theta, "30")
    assert parsed.components is None
    assert "between 0° and 180°" in parsed.error


@pytest.mark.parametrize("theta", ["0", "90", "180"])
def test_theta_at_the_ends_of_its_range_is_allowed(theta: str) -> None:
    assert parse_angles("2", theta, "30").components is not None


def test_phi_outside_one_turn_is_accepted_and_normalized() -> None:
    # Unlike theta, phi is defined for any value once brought into range.
    assert parse_angles("2", "60", "390").components == pytest.approx(
        parse_angles("2", "60", "30").components
    )


def test_an_empty_angle_field_says_which_one() -> None:
    assert parse_angles("2", "", "30").error == "Enter a value for θ."

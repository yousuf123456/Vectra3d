"""The rules behind the action panel: creating (F-04) and editing (F-08).

Only the rules are tested here, not the widgets: what a typed form means,
what text the edit fields should hold for a given vector, and when those
fields may be rewritten. Those are what the criteria are about. No window is
opened; the widgets are checked by hand, following the step's report.
"""

from __future__ import annotations

import math

import pytest

from vectra3d.state.models import Vector
from vectra3d.ui.action_panel import (
    angle_fields,
    component_fields,
    parse_angles,
    parse_components,
    parse_number,
    phi_is_undefined,
    should_refill,
)


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


# --- Numbers that float() accepts but a vector cannot have ---


@pytest.mark.parametrize("text", ["nan", "NaN", "-nan"])
def test_nan_is_refused(text: str) -> None:
    # float() parses these happily. Left alone, they reach the scene sizing,
    # where every comparison against a nan is false and the search for a
    # fitting extent never ends.
    value, error = parse_number(text, "x")
    assert value is None
    assert "must be a number" in error


@pytest.mark.parametrize("text", ["inf", "-inf", "Infinity", "1e400"])
def test_infinity_is_refused(text: str) -> None:
    # "1e400" is the one a student could type by accident: it is an ordinary
    # looking number that overflows to infinity.
    value, error = parse_number(text, "x")
    assert value is None
    assert "too large" in error


def test_a_component_form_with_infinity_creates_nothing() -> None:
    parsed = parse_components("1e400", "1", "1")
    assert parsed.components is None
    assert parsed.error is not None


def test_an_angle_form_with_nan_creates_nothing() -> None:
    parsed = parse_angles("nan", "60", "30")
    assert parsed.components is None
    assert parsed.error is not None


def test_very_large_but_finite_numbers_are_still_allowed() -> None:
    # The rule is about values that are not numbers, not about big vectors.
    assert parse_components("1e300", "0", "0").components == (1e300, 0.0, 0.0)


# --- What the edit fields show (F-08) ---


def test_components_fill_the_fields_at_two_decimals() -> None:
    assert component_fields((1.0, -2.5, 3.14159)) == ("1.00", "-2.50", "3.14")


def test_a_field_never_shows_negative_zero() -> None:
    # Section 2.5, the same rule the info panel follows.
    assert component_fields((-0.001, 0.0, 1.0))[0] == "0.00"


def test_angles_fill_the_fields_at_two_decimals() -> None:
    # (0, 4, 3): r = 5, theta = arccos(3/5) = 53.13 degrees, phi = 90.
    assert angle_fields((0.0, 4.0, 3.0)) == ("5.00", "53.13", "90.00")


def test_a_vector_on_the_z_axis_fills_phi_with_zero() -> None:
    # Undefined there, but the field has to hold something Apply can read.
    assert angle_fields((0.0, 0.0, 6.0)) == ("6.00", "0.00", "0.00")


def test_the_zero_vector_fills_every_angle_field_with_zero() -> None:
    assert angle_fields((0.0, 0.0, 0.0)) == ("0.00", "0.00", "0.00")


def test_the_angle_fields_can_be_read_back_by_the_parser() -> None:
    # The round trip the student makes without noticing: the fields are
    # filled from a vector, and Apply parses that same text back.
    components = (1.0, -2.0, 2.0)
    parsed = parse_angles(*angle_fields(components))
    assert parsed.error is None
    assert parsed.components == pytest.approx(components, abs=5e-3)


def test_the_component_fields_can_be_read_back_by_the_parser() -> None:
    parsed = parse_components(*component_fields((3.0, 0.0, -4.0)))
    assert parsed.components == (3.0, 0.0, -4.0)


@pytest.mark.parametrize(
    ("components", "undefined"),
    [
        ((0.0, 0.0, 5.0), True),  # up the z axis
        ((0.0, 0.0, -5.0), True),  # down it
        ((1.0, 0.0, 5.0), False),  # leaning, so phi means something
        ((0.0, 1.0, 5.0), False),
        ((1.0, 1.0, 0.0), False),  # flat in the XY plane
    ],
)
def test_phi_is_undefined_only_along_the_z_axis(
    components: tuple[float, float, float], undefined: bool
) -> None:
    assert phi_is_undefined(components) is undefined


# --- When the edit fields are rewritten (F-08) ---


def vector(name: str, components: tuple[float, float, float]) -> Vector:
    return Vector(name=name, components=components)


def test_the_fields_are_filled_when_nothing_has_been_shown_yet() -> None:
    assert should_refill(None, vector("A", (1.0, 0.0, 0.0))) is True


def test_the_fields_are_left_alone_when_the_same_vector_is_unchanged() -> None:
    # This is the case that protects half-typed text: ticking another card
    # or deleting a different vector notifies, but changes nothing here.
    shown = ("A", (1.0, 0.0, 0.0))
    assert should_refill(shown, vector("A", (1.0, 0.0, 0.0))) is False


def test_the_fields_are_refilled_when_another_vector_becomes_active() -> None:
    shown = ("A", (1.0, 0.0, 0.0))
    assert should_refill(shown, vector("B", (1.0, 0.0, 0.0))) is True


def test_the_fields_are_refilled_when_the_same_vector_moved() -> None:
    # What matters from G5: a vector steered by hand must not leave stale
    # numbers here for Apply to put back.
    shown = ("A", (1.0, 0.0, 0.0))
    assert should_refill(shown, vector("A", (1.0, 2.0, 0.0))) is True


def test_the_fields_are_cleared_when_the_last_vector_goes() -> None:
    assert should_refill(("A", (1.0, 0.0, 0.0)), None) is True


def test_nothing_happens_while_the_scene_stays_empty() -> None:
    assert should_refill(None, None) is False


def test_a_reused_letter_with_different_components_refills() -> None:
    # A is deleted and a new vector takes the letter back; same name, and
    # the fields must not keep showing the vector that is gone.
    shown = ("A", (1.0, 0.0, 0.0))
    assert should_refill(shown, vector("A", (0.0, 0.0, 9.0))) is True

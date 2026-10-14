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
from vectra3d.render.scene import MAX_COMPONENT
from vectra3d.ui.action_panel import (
    angle_fields,
    component_fields,
    parse_angles,
    parse_components,
    parse_number,
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


# --- The magnitude and direction angles form ---
#
# |v|, alpha, beta, gamma, the textbook way (`interaction-spec.md` 2.3).


def test_valid_angles_are_converted() -> None:
    # |A| = 10, alpha 60, beta 45, gamma 120: A = 10 (1/2, 1/sqrt 2, -1/2).
    parsed = parse_angles("10", "60", "45", "120")
    assert parsed.error is None
    assert parsed.components == pytest.approx((5.0, 10 / math.sqrt(2), -5.0))


def test_a_vector_along_an_axis_is_exact() -> None:
    assert parse_angles("3", "90", "180", "90").components == (0.0, -3.0, 0.0)


def test_a_magnitude_of_zero_is_refused() -> None:
    # A zero magnitude is the zero vector by another name.
    parsed = parse_angles("0", "60", "45", "120")
    assert parsed.components is None
    assert "greater than 0" in parsed.error


def test_a_negative_magnitude_is_refused() -> None:
    parsed = parse_angles("-3", "60", "45", "120")
    assert parsed.components is None
    assert "greater than 0" in parsed.error


@pytest.mark.parametrize(
    ("angles", "name"),
    [(("-1", "90", "90"), "α"), (("90", "181", "90"), "β"), (("90", "90", "360"), "γ")],
)
def test_an_angle_outside_0_to_180_is_refused_by_name(angles, name: str) -> None:
    parsed = parse_angles("2", *angles)
    assert parsed.components is None
    assert parsed.error == f"{name} must be between 0° and 180°."


def test_angles_that_do_not_fit_together_are_refused_with_their_sum() -> None:
    # 60 degrees from every axis: cos squared is a quarter each, 0.75 in all.
    parsed = parse_angles("2", "60", "60", "60")
    assert parsed.components is None
    assert parsed.error == (
        "These angles do not fit together: cos²α + cos²β + cos²γ = 0.750, "
        "but it must be 1."
    )


def test_rounded_textbook_angles_are_accepted() -> None:
    # The diagonal (1, 1, 1) is 54.7356 degrees from each axis; rounded to a
    # tenth the sum is 1.0026, within the 0.01 allowed, and the length is
    # still exactly what was typed.
    parsed = parse_angles("6", "54.7", "54.7", "54.7")
    assert parsed.error is None
    assert math.hypot(*parsed.components) == pytest.approx(6.0, abs=1e-12)


def test_just_outside_the_tolerance_is_refused() -> None:
    # alpha 0 alone sums to 1; beta 84 adds cos^2 84 = 0.0109.
    assert parse_angles("1", "0", "84", "90").components is None
    # beta 85 adds 0.0076, inside.
    assert parse_angles("1", "0", "85", "90").components is not None


def test_an_empty_angle_field_says_which_one() -> None:
    assert parse_angles("2", "60", "", "120").error == "Enter a value for β."


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
    parsed = parse_angles("nan", "60", "45", "120")
    assert parsed.components is None
    assert parsed.error is not None


def test_large_numbers_are_allowed_up_to_what_can_be_drawn() -> None:
    # The rule is not a dislike of big vectors: anything the scene can draw is
    # accepted, which is far beyond any exercise.
    assert parse_components("1e30", "0", "0").components == (1e30, 0.0, 0.0)
    assert parse_components(str(MAX_COMPONENT), "0", "0").error is None


def test_numbers_too_large_to_draw_are_refused() -> None:
    # This replaces a test that asserted 1e300 was allowed, written at the G1
    # review on the belief that only values which are not numbers could hurt.
    # That belief was wrong: VTK holds point coordinates as 32-bit floats, so
    # 1e300 builds geometry of infinity and takes the window down. The test
    # fired the moment the refusal arrived, exactly as it should have.
    parsed = parse_components("1e300", "0", "0")
    assert parsed.components is None
    assert parsed.error is not None
    assert "too large" in parsed.error


# --- What the edit fields show (F-08) ---


def test_components_fill_the_fields_at_two_decimals() -> None:
    assert component_fields((1.0, -2.5, 3.14159)) == ("1.00", "-2.50", "3.14")


def test_a_field_never_shows_negative_zero() -> None:
    # Section 2.5, the same rule the info panel follows.
    assert component_fields((-0.001, 0.0, 1.0))[0] == "0.00"


def test_angles_fill_the_fields_at_two_decimals() -> None:
    # (0, 4, 3): |v| = 5, alpha 90, beta = arccos(4/5) = 36.87,
    # gamma = arccos(3/5) = 53.13.
    assert angle_fields((0.0, 4.0, 3.0)) == ("5.00", "90.00", "36.87", "53.13")


def test_a_vector_on_the_z_axis_has_every_angle_defined() -> None:
    # The old phi had no value here; direction angles always do.
    assert angle_fields((0.0, 0.0, 6.0)) == ("6.00", "90.00", "90.00", "0.00")


def test_the_zero_vector_fills_every_angle_field_with_zero() -> None:
    assert angle_fields((0.0, 0.0, 0.0)) == ("0.00",) * 4


@pytest.mark.parametrize(
    "components", [(1.0, -2.0, 2.0), (0.0, 0.0, 6.0), (-7.5, 0.25, 11.0), (1.0, 1.0, 1.0)]
)
def test_the_angle_fields_can_be_read_back_by_the_parser(components) -> None:
    # The round trip the student makes without noticing: the fields are
    # filled from a vector, and Apply parses that same text back. Rounded to
    # two decimals, the angles must still fit together.
    parsed = parse_angles(*angle_fields(components))
    assert parsed.error is None
    assert parsed.components == pytest.approx(components, abs=5e-3)


def test_the_component_fields_can_be_read_back_by_the_parser() -> None:
    parsed = parse_components(*component_fields((3.0, 0.0, -4.0)))
    assert parsed.components == (3.0, 0.0, -4.0)


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

"""Display rules for numbers (`interaction-spec.md` section 2.5)."""

from __future__ import annotations

import pytest

from vectra3d.core.formatting import (
    EM_DASH,
    format_angle,
    format_number,
    format_triple,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "0.00"),
        (3.0, "3.00"),
        (3.5, "3.50"),
        (-2.0, "-2.00"),
        (45.0, "45.00"),
        (1234.5, "1234.50"),
    ],
)
def test_two_decimals_always(value: float, expected: str) -> None:
    assert format_number(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (3.456, "3.46"),
        (3.454, "3.45"),
        (-3.456, "-3.46"),
    ],
)
def test_rounding(value: float, expected: str) -> None:
    assert format_number(value) == expected


@pytest.mark.parametrize("value", [-0.0, -0.001, -0.0001, -1e-17])
def test_negative_zero_is_never_shown(value: float) -> None:
    # A component that rounds to zero from below must not read "-0.00", which
    # looks like a different number from zero.
    assert format_number(value) == "0.00"


def test_a_value_that_rounds_to_zero_from_above_is_also_plain_zero() -> None:
    assert format_number(0.001) == "0.00"


def test_small_negatives_that_survive_rounding_keep_their_sign() -> None:
    # Only values that actually round to zero lose the sign.
    assert format_number(-0.006) == "-0.01"


def test_the_stored_value_is_untouched() -> None:
    # Formatting produces text; it never changes the number it was given.
    value = -1e-17
    format_number(value)
    assert value == -1e-17


# --- Angles and undefined values (interaction-spec.md 2.4 and 2.5) ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, "0.00°"),
        (45.0, "45.00°"),
        (64.89590974977862, "64.90°"),
        (180.0, "180.00°"),
        (90.0, "90.00°"),
    ],
)
def test_angles_get_two_decimals_and_a_degree_sign(
    value: float, expected: str
) -> None:
    assert format_angle(value) == expected


def test_an_angle_that_rounds_to_zero_from_below_is_not_negative_zero() -> None:
    # An axis-aligned vector can give an angle a hair under zero. The rule
    # against "-0.00" applies to angles exactly as it does to components.
    assert format_angle(-1e-9) == "0.00°"


def test_an_undefined_angle_is_an_em_dash() -> None:
    # Only the zero vector produces this, and `direction_angles` hands back
    # None rather than a number for it.
    assert format_angle(None) == EM_DASH


def test_a_triple_is_written_as_one_bracketed_value() -> None:
    assert format_triple((0.4242640687, 0.5656854249, 0.7071067811)) == (
        "(0.42, 0.57, 0.71)"
    )


def test_a_triple_keeps_the_negative_zero_rule() -> None:
    assert format_triple((-1e-18, 1.0, 0.0)) == "(0.00, 1.00, 0.00)"


def test_an_undefined_triple_is_an_em_dash() -> None:
    assert format_triple(None) == EM_DASH

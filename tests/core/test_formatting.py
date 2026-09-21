"""Display rules for numbers (`interaction-spec.md` section 2.5)."""

from __future__ import annotations

import pytest

from vectra3d.core.formatting import format_number


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

"""Turning numbers into the text the student reads.

The display rules from `interaction-spec.md` section 2.5. Everything in the
app calculates at full precision and rounds only here, at the moment of
showing a value, so rounding never feeds back into the maths.

"""

from __future__ import annotations

DECIMALS = 2

# What is shown where there is no value to show. Section 2.4 calls the
# magnitude, angles and unit vector of the zero vector undefined, and an em
# dash says "there is nothing here" without pretending to be a number, which
# a 0.00 would.
EM_DASH = "—"

UNDEFINED_NOTE = "zero vector has no direction"

DEGREE = "°"


def format_number(value: float) -> str:
    """Format a value for display: two decimals, and never "-0.00".

    A tiny negative value such as -0.001 rounds to -0.00, which looks like a
    different number from zero and invites the question "how can a component
    be negative zero?". Section 2.5 says to show 0.00 instead. Note this
    changes only the text: the stored value keeps its sign and full
    precision.
    """
    text = f"{value:.{DECIMALS}f}"
    if float(text) == 0.0:
        return f"{0.0:.{DECIMALS}f}"
    return text


def format_angle(value: float | None) -> str:
    """Format an angle for display: two decimals and a degree sign.

    `None` means the angle is undefined, which happens only for the zero
    vector, and shows as an em dash. Passing it through here rather than
    checking at every call site keeps section 2.4's rule in one place.
    """
    if value is None:
        return EM_DASH
    return f"{format_number(value)}{DEGREE}"


def format_triple(values: tuple[float, float, float] | None) -> str:
    """Format three numbers as one value, for the unit vector.

    Written on one line because a unit vector is read as a direction rather
    than as three separate quantities, and because three more rows would
    crowd an already narrow panel. `None` gives an em dash, as above.
    """
    if values is None:
        return EM_DASH
    return f"({', '.join(format_number(value) for value in values)})"

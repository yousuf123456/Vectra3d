"""Turning numbers into the text the student reads.

The display rules from `interaction-spec.md` section 2.5. Everything in the
app calculates at full precision and rounds only here, at the moment of
showing a value, so rounding never feeds back into the maths.

Angles, and the em dash for values that are undefined for the zero vector,
arrive with the full info panel in G2.3.
"""

from __future__ import annotations

DECIMALS = 2


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

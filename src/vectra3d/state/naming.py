"""Names and colors for vectors.

Vectors are named in textbook style with capital letters, and each letter
carries its own color. A new vector always takes the lowest free letter, so a
deleted letter comes back into use: delete B and the next vector is B again.

Color is derived from the letter rather than stored on the vector, which keeps
the two rules as one piece of bookkeeping. It also means a reused letter
reappears in the color the student already associates with that row.
"""

from __future__ import annotations

from collections.abc import Iterable

# The most vectors that can exist at once (`features.md`, global vector rules).
MAX_VECTORS = 10

# Vector names, in the order they are handed out.
NAMES: tuple[str, ...] = tuple("ABCDEFGHIJ")

# One color per letter, in the same order as NAMES.
#
# The axes and the component vectors own red, green and blue
# (`interaction-spec.md` section 2.1), so no vector may look like any of them.
# These ten hues stay clear of those three and of each other, and are dark
# enough to read against the white background the 3D view currently uses.
VECTOR_COLORS: tuple[str, ...] = (
    "#E67E22",  # A  orange
    "#B8860B",  # B  dark gold
    "#808000",  # C  olive
    "#6B8E23",  # D  olive drab
    "#009B77",  # E  jade
    "#008B8B",  # F  teal
    "#0077B6",  # G  ocean
    "#7D3C98",  # H  violet
    "#C2185B",  # I  raspberry
    "#8B4513",  # J  brown
)

# The color reserved for a temporary operation result (`features.md`, global
# rules for operation results). No regular vector ever uses it. Near-black is
# the furthest thing on a white background from ten saturated hues and from
# the red, green and blue axes.
RESULT_COLOR = "#111111"


def next_free_name(used: Iterable[str]) -> str | None:
    """Return the lowest unused vector name, or None if all are taken."""
    taken = set(used)
    for name in NAMES:
        if name not in taken:
            return name
    return None


def color_for(name: str) -> str:
    """Return the color belonging to a vector name.

    Raises KeyError if the name is not one of the ten vector names, because
    that means a vector was built outside the naming rules.
    """
    try:
        return VECTOR_COLORS[NAMES.index(name)]
    except ValueError:
        raise KeyError(f"{name!r} is not a vector name") from None

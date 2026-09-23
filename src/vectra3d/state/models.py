"""The data a vector is made of.

`Vector` is frozen: changing one means building a replacement with
`dataclasses.replace`, never editing it in place. That does two useful things.
Undo can snapshot the whole scene by copying a dictionary instead of deep
copying every vector, and no part of the app can quietly change a vector
without going through `actions.py`.

Components are plain tuples rather than NumPy arrays. The math layer (`core`)
is where NumPy belongs; here the values are only stored and passed around.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

# A point in the scene: x, y, z.
Point = tuple[float, float, float]

ORIGIN: Point = (0.0, 0.0, 0.0)


class Operation(Enum):
    """Which operation made a result.

    A result has to remember this, because it is worked out again whenever one
    of its vectors changes and the answer depends on *how* it was made. Before
    this existed, every result was refreshed by adding its sources up, which
    was right for the only operation there was and would have turned A - B
    silently into A + B the first time B was edited.

    An enum rather than a stored function, so a snapshot stays plain data and
    undo keeps working without knowing anything about operations.
    """

    SUM = "sum"
    DIFFERENCE = "difference"


@dataclass(frozen=True)
class Result:
    """The temporary answer to an operation: a resultant, a difference, a
    multiple (`features.md`, global rules for operation results).

    Deliberately **not** a `Vector`. It has no letter and so no colour of its
    own - every result is drawn in the one reserved colour - it does not count
    towards the ten-vector limit, and it cannot be locked, edited, ticked or
    made active. Only one exists at a time, and running another operation
    replaces it. Giving it its own type is what makes all of that structural
    rather than a set of rules every caller has to remember.

    `sources` is the letters the result was worked out from, which is what
    makes it live: when one of those vectors changes the result is worked out
    again, and when one of them is deleted the result goes.

    `expression` is how the student reads it - "A + B + C", "A - B", "2.50*A".
    It is built when the result is made, because that is the only moment that
    knows which operation ran; nothing can reconstruct it from the numbers
    afterwards.

    `operation` is what lets it be worked out again correctly when one of its
    vectors changes. `sources` alone is not enough: A and B can be added or
    subtracted, and the difference between those two answers is the whole
    point.
    """

    expression: str
    components: Point
    sources: tuple[str, ...]
    operation: Operation = Operation.SUM
    tail: Point = ORIGIN


@dataclass(frozen=True)
class Vector:
    """One vector in the scene.

    `tail` is always the origin in the MVP, but it is stored rather than
    assumed so that free vectors (`project-overview.md`, after the MVP) can be
    added later without rewriting everything that reads a vector.

    `locked` is here from G2.3 because F-11 asks the info panel to show lock
    status. Nothing can set it until F-09a arrives in G2.5 with the toggle and
    the rules that go with it - a locked vector ignoring edits, and refusing to
    be deleted - so until then it is simply false everywhere and the indicator
    never appears.
    """

    name: str
    components: Point
    tail: Point = ORIGIN
    locked: bool = False

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

# A point in the scene: x, y, z.
Point = tuple[float, float, float]

ORIGIN: Point = (0.0, 0.0, 0.0)


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

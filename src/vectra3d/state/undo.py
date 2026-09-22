"""Undo and redo, kept deliberately simple (F-19).

A snapshot of the whole scene is taken before each change, and undo puts a
snapshot back. `features.md` says this in as many words: store a snapshot of
all vectors before each change, and do not build a command system. A command
system would mean every action carrying its own inverse - how to un-delete,
how to un-lock - and with at most ten frozen vectors there is nothing to gain
from it and a great deal to get wrong.

**What a snapshot holds** is the vectors and which one was active. The active
vector is in there because creating a vector makes it active, so undoing a
create has to leave the highlight somewhere honest, and where it was before
is the only honest answer.

**The temporary result is in there too**, added at G3.2. This is a departure
from the line drawn below, and a deliberate one: F-19 names "saving a result
as a vector" as a thing undo must cover, and undoing that save leaves the
scene wrong unless the result comes back to stand where the saved vector was.
`store.restore` drops a restored result whose input vectors are no longer in
the scene.

**What it leaves out** is everything about display: which vectors are ticked
for an operation, and which one is showing its components or its shadows.
F-19 says undo covers changes to the vectors and not display options, and
those three were each decided to sit outside undo when they were built
(G2.2, G2.6, G2.7). So a vector restored by undo comes back unticked, with
its overlays off.

Because `Vector` is frozen, a snapshot is a plain dictionary copy rather than
a deep one: nothing can change a vector in place, so two snapshots sharing a
vector object can never disagree. That is what makes this cheap enough to do
before every change.
"""

from __future__ import annotations

from dataclasses import dataclass

from vectra3d.state.models import Result, Vector

# How many changes can be taken back (F-19). Older steps fall off the end.
MAX_STEPS = 20


@dataclass(frozen=True)
class Snapshot:
    """The scene as it was: every vector, which one was active, and the result."""

    vectors: dict[str, Vector]
    active: str | None
    result: Result | None = None


class History:
    """The steps that can be taken back, and the ones taken back so far.

    `past` holds the scene as it was before each recorded change, oldest
    first. `future` holds the states undone out of, so redo can put them
    back. Recording a new change clears `future`, because the branch it
    described no longer leads anywhere (F-19).
    """

    def __init__(self, limit: int = MAX_STEPS) -> None:
        self._limit = limit
        self._past: list[Snapshot] = []
        self._future: list[Snapshot] = []

    @property
    def can_undo(self) -> bool:
        return bool(self._past)

    @property
    def can_redo(self) -> bool:
        return bool(self._future)

    def record(self, snapshot: Snapshot) -> None:
        """Remember the scene as it is, before something changes it.

        Called by `actions.py` before each change, and only when the change
        actually happens: an action that refuses - an eleventh vector, or
        deleting a locked one - leaves the scene alone and so must leave the
        history alone too, or undo would appear to do nothing.
        """
        self._past.append(snapshot)
        if len(self._past) > self._limit:
            # Oldest first, so the twenty most recent survive.
            del self._past[0]
        self._future.clear()

    def undo(self, current: Snapshot) -> Snapshot | None:
        """Step back. Returns the scene to restore, or None if there is none.

        `current` is the scene as it is now, which is kept so redo can come
        back to it.
        """
        if not self._past:
            return None

        self._future.append(current)
        return self._past.pop()

    def redo(self, current: Snapshot) -> Snapshot | None:
        """Step forward again. Returns the scene to restore, or None."""
        if not self._future:
            return None

        self._past.append(current)
        return self._future.pop()

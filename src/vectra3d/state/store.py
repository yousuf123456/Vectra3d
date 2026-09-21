"""Where the vectors live, and how the rest of the app hears about changes.

The store holds the vectors, remembers which one is active, and remembers
which ones are ticked for an operation. The ticks live here rather than in the
info panel for a practical reason: the panel rebuilds its cards from scratch
on every change, so a tick kept in a checkbox would be wiped by any unrelated
edit. Keeping them here also means G3's Resultant button reads them from the
same place everything else reads state from. It does not
decide what is allowed: the rules (the ten-vector limit, which letter comes
next, what happens to the active vector after a deletion) live in
`actions.py`, which is the only place that should call the methods here that
change anything.

Listeners are plain callables, not Qt signals. Keeping Qt out of this layer
means the whole of `state` can be tested without starting an application. The
window wraps a listener around a Qt signal when it needs one.

A change event carries nothing: it says "something changed, read me again".
With at most ten vectors there is nothing to gain from describing the change,
and a listener that re-reads the store can never fall out of step with it.
"""

from __future__ import annotations

from collections.abc import Callable

from vectra3d.state.models import Vector


class VectorStore:
    """The vectors in the scene and the active one."""

    def __init__(self) -> None:
        self._vectors: dict[str, Vector] = {}
        self._active: str | None = None
        self._selected: set[str] = set()
        self._listeners: list[Callable[[], None]] = []

    # --- Reading ---

    @property
    def vectors(self) -> tuple[Vector, ...]:
        """Every vector, in name order.

        Name order rather than creation order, so a reused letter reappears in
        the row the student last saw it in.
        """
        return tuple(self._vectors[name] for name in sorted(self._vectors))

    @property
    def names(self) -> tuple[str, ...]:
        """Every name currently in use, in name order."""
        return tuple(sorted(self._vectors))

    @property
    def count(self) -> int:
        return len(self._vectors)

    @property
    def active_name(self) -> str | None:
        return self._active

    @property
    def active(self) -> Vector | None:
        """The vector gestures and edits act on, or None if there are none."""
        if self._active is None:
            return None
        return self._vectors[self._active]

    def get(self, name: str) -> Vector | None:
        return self._vectors.get(name)

    @property
    def selected(self) -> tuple[str, ...]:
        """The names ticked for an operation, in name order.

        Separate from the active vector (F-05a). A student can tick A and B
        for a resultant while C stays active to be steered. Returned as a
        tuple so no caller can change the selection except through
        `actions.py`.
        """
        return tuple(sorted(self._selected))

    def is_selected(self, name: str) -> bool:
        return name in self._selected

    # --- Listening ---

    def subscribe(self, listener: Callable[[], None]) -> None:
        """Call `listener` after every change to the vectors or the active one."""
        self._listeners.append(listener)

    def notify(self) -> None:
        """Tell every listener that the store has changed.

        Called by `actions.py` once per action, after all of its changes are
        in place, so listeners never see a half-finished change.
        """
        for listener in self._listeners:
            listener()

    # --- Changing (called only by actions.py) ---

    def put(self, vector: Vector) -> None:
        """Add a vector or replace the one with the same name."""
        self._vectors[vector.name] = vector

    def remove(self, name: str) -> None:
        del self._vectors[name]
        # Pruned here rather than in `actions.py` so no route can leave a tick
        # behind. Letters are reused, so a stale name is not merely untidy: it
        # would make the next vector to take that letter appear ticked.
        self._selected.discard(name)

    def clear(self) -> None:
        self._vectors.clear()
        self._selected.clear()

    def set_active(self, name: str | None) -> None:
        if name is not None and name not in self._vectors:
            raise KeyError(f"no vector named {name!r}")
        self._active = name

    def set_selected(self, name: str, selected: bool) -> None:
        if name not in self._vectors:
            raise KeyError(f"no vector named {name!r}")
        if selected:
            self._selected.add(name)
        else:
            self._selected.discard(name)

    def clear_selection(self) -> None:
        self._selected.clear()

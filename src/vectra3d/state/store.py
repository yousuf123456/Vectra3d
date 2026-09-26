"""Where the vectors live, and how the rest of the app hears about changes.

The store holds the vectors, remembers which one is active, remembers which
ones are ticked for an operation, and remembers which one is showing its
components and which one is showing its shadows. The ticks live here rather than in the
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

from vectra3d.state.models import Result, Settings, Vector
from vectra3d.state.undo import History, Snapshot


class VectorStore:
    """The vectors in the scene and the active one."""

    def __init__(self) -> None:
        self._vectors: dict[str, Vector] = {}
        self._active: str | None = None
        self._selected: set[str] = set()
        self._components_shown: str | None = None
        self._projections_shown: str | None = None
        # The one temporary operation result, and why the last one was
        # dropped if it was. The reason is kept because a result can vanish
        # without the student touching it - editing a vector until the sum
        # overflows - and a thing that disappears with no explanation reads
        # as a bug.
        self._result: Result | None = None
        self._result_error: str | None = None
        self._listeners: list[Callable[[], None]] = []
        # The gesture settings. Not part of the scene: outside undo, and
        # untouched by clearing it.
        self._settings = Settings()
        # The steps that can be taken back (F-19). The store owns it so that
        # every action keeps its one-argument signature, and so that G5's
        # gesture engine records through the same place the panel does.
        self.history = History()
        # The scene as it was when a hand gesture began, or None when no
        # gesture is running. A gesture changes the vectors on every frame;
        # this is what lets it become one undo step when it ends, or be put
        # back exactly if it is cancelled (`interaction-spec.md` section 5).
        self._gesture_before: Snapshot | None = None

    # --- Reading ---

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def gesture_in_progress(self) -> bool:
        """Whether a hand gesture is changing the vectors right now.

        While it is, changes are not recorded one by one, and the scene does
        not rescale (`interaction-spec.md` section 3).
        """
        return self._gesture_before is not None

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

    def snapshot(self) -> Snapshot:
        """The scene as it is now, for the history to hold on to.

        A plain dictionary copy, not a deep one: `Vector` is frozen, so two
        snapshots sharing a vector object can never come to disagree. That
        is what makes taking one before every change cheap.
        """
        return Snapshot(
            vectors=dict(self._vectors), active=self._active, result=self._result
        )

    def restore(self, snapshot: Snapshot) -> None:
        """Put a remembered scene back, replacing what is there now.

        Only called by `actions.undo`/`actions.redo`. Ticks and the display
        overlays are not in a snapshot (see `undo.py`), so they are pruned
        against what actually came back rather than being restored: a name
        that is no longer in the scene must not keep a tick or an overlay.
        """
        self._vectors = dict(snapshot.vectors)
        self._active = snapshot.active if snapshot.active in self._vectors else None
        self._result = snapshot.result
        self._result_error = None
        if self._result is not None and not set(self._result.sources) <= set(
            self._vectors
        ):
            # A result outlives an undo only while every vector it was worked
            # out from is still there. Coming back as a black arrow labelled
            # with a letter the scene no longer has would be worse than not
            # coming back at all.
            self._result = None
        self._selected &= set(self._vectors)
        if self._components_shown not in self._vectors:
            self._components_shown = None
        if self._projections_shown not in self._vectors:
            self._projections_shown = None

    @property
    def result(self) -> Result | None:
        """The temporary operation result, if one is showing."""
        return self._result

    @property
    def result_error(self) -> str | None:
        """Why the last result was dropped, or None."""
        return self._result_error

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

    @property
    def components_shown(self) -> str | None:
        """The one vector whose x, y, z parts are drawn, or None (F-13a).

        One at a time, not a set. Every vector resolves onto the same three
        axes, so two vectors showing components put two arrows of the same
        colour on the same line, and their value labels crowd the same
        corner near the origin. Showing one is what makes it readable.

        Holding the name rather than a set of them is what makes that a fact
        rather than a promise: there is no state in which two are shown.

        A display setting rather than anything about the vector itself, which
        is why it lives here rather than on `Vector`, and why F-19 leaves it
        out of undo. Kept in the store for the same reason the ticks are: the
        info panel rebuilds every card on every change, so a state held in a
        button would not survive an unrelated edit.
        """
        return self._components_shown

    def is_components_shown(self, name: str) -> bool:
        return self._components_shown == name

    @property
    def projections_shown(self) -> str | None:
        """The one vector whose shadows on the three planes are drawn (F-14).

        One at a time and held by name, for the same reason as
        `components_shown`: two vectors projecting would put overlapping
        arrows on the same three planes.

        Independent of `components_shown`, though. The two answer different
        questions - what a vector is made of, and what it looks like from
        each side - and either or both can be on, on the same vector or on
        different ones.
        """
        return self._projections_shown

    def is_projections_shown(self, name: str) -> bool:
        return self._projections_shown == name

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
        # Pruned here rather than in `actions.py` so no route can leave a mark
        # behind. Letters are reused, so a stale name is not merely untidy: it
        # would make the next vector to take that letter appear ticked, or
        # arrive with someone else's components already drawn.
        self._selected.discard(name)
        if self._components_shown == name:
            self._components_shown = None
        if self._projections_shown == name:
            self._projections_shown = None

    def clear(self) -> None:
        self._vectors.clear()
        self._selected.clear()
        self._components_shown = None
        self._projections_shown = None
        self._result = None
        self._result_error = None

    def set_settings(self, settings: Settings) -> None:
        self._settings = settings

    def set_active(self, name: str | None) -> None:
        if name is not None and name not in self._vectors:
            raise KeyError(f"no vector named {name!r}")
        self._active = name

    def set_components_shown(self, name: str, shown: bool) -> None:
        """Show this vector's components, or hide them.

        Showing one replaces whichever was showing before, so nothing else
        has to remember to turn the previous one off.
        """
        if name not in self._vectors:
            raise KeyError(f"no vector named {name!r}")
        if shown:
            self._components_shown = name
        elif self._components_shown == name:
            self._components_shown = None

    def set_projections_shown(self, name: str, shown: bool) -> None:
        """Show this vector's shadows, or hide them.

        Showing one replaces whichever was showing before, so nothing else
        has to remember to turn the previous one off.
        """
        if name not in self._vectors:
            raise KeyError(f"no vector named {name!r}")
        if shown:
            self._projections_shown = name
        elif self._projections_shown == name:
            self._projections_shown = None

    def set_result(self, result: Result | None) -> None:
        """Put a result in place of whatever was there, or clear it.

        Only one exists at a time, so this replaces rather than adds. Setting
        a result clears any message about the last one, because the message
        described a result that no longer matters.
        """
        self._result = result
        self._result_error = None

    def set_result_error(self, message: str | None) -> None:
        """Record why the result was dropped, for the panel to show."""
        self._result_error = message

    def set_selected(self, name: str, selected: bool) -> None:
        if name not in self._vectors:
            raise KeyError(f"no vector named {name!r}")
        if selected:
            self._selected.add(name)
        else:
            self._selected.discard(name)

    def clear_selection(self) -> None:
        self._selected.clear()

    def start_gesture(self, before: Snapshot) -> None:
        """Remember the scene as it was when a gesture began."""
        self._gesture_before = before

    def end_gesture(self) -> Snapshot | None:
        """Forget the gesture, handing back the scene it began from."""
        before, self._gesture_before = self._gesture_before, None
        return before

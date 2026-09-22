"""Every allowed change to the vectors.

This is the only sanctioned way to change state. The action panel calls these
functions, and from G5 the gesture engine calls the same ones through its
intents. That is what guarantees two things the specs require: every gesture
has a panel equivalent, and every change passes through one place, which is
where undo will record its snapshots (F-19).

Each action makes its changes and then notifies the store's listeners exactly
once, so the info panel and the 3D view never redraw a half-finished change.

Actions that change the vectors record a snapshot first, which is what makes
undo work (F-19): creating, editing, locking, deleting and clearing. They
record only once the change is certain to happen, so a refused action - an
eleventh vector, or deleting a locked one - leaves the history alone, or undo
would appear to do nothing.

Choosing the active vector, ticking one for an operation, and switching the
component and shadow overlays on and off are *not* recorded. F-19 keeps undo
for changes to the vectors themselves and leaves out display options.

**Keeping the result live.** A result is worked out from named vectors, so
anything that changes one of those vectors has to work it out again, and
anything that removes one has to take the result away. Rather than leaving
each action to remember that, the actions that touch components call
`_refresh_result` before they notify. That is one place to get right, and it
is what makes the result live for hand gestures in G5 without any further
work: the gesture engine calls these same actions.
"""

from __future__ import annotations

from dataclasses import replace

from vectra3d.core.operations import resultant
from vectra3d.state import naming
from vectra3d.state.models import ORIGIN, Point, Result, Vector
from vectra3d.state.store import VectorStore

# The fewest vectors an operation can be run over (F-15).
MIN_FOR_RESULTANT = 2

# What the student is told when a result cannot be worked out as a number.
TOO_LARGE = "{expression} is too large to show."


def create_vector(
    store: VectorStore, components: Point, tail: Point = ORIGIN
) -> Vector | None:
    """Create a vector and make it active.

    It takes the lowest free name (`naming.next_free_name`). Returns the new
    vector, or None if ten already exist, which is the caller's cue to show
    the limit message (F-04, F-03).

    A zero vector is accepted here. Typed input rejects it (F-04), but an
    operation result can be zero and still be saved as a vector (F-16), so the
    rule belongs to the input form rather than to the store.
    """
    name = naming.next_free_name(store.names)
    if name is None:
        return None

    store.history.record(store.snapshot())
    vector = Vector(name=name, components=components, tail=tail)
    store.put(vector)
    store.set_active(name)
    store.notify()
    return vector


def edit_vector(store: VectorStore, name: str, components: Point) -> bool:
    """Give an existing vector new components (F-08).

    The vector keeps its name, and so its colour, and keeps its tail and its
    lock state. Only what it points at changes. Returns False if there is no
    such vector, or if it is locked.

    A locked vector is refused here rather than only in the panel, which
    disables the form for one. F-09a says a locked vector ignores all edits,
    and in G5 the gesture engine reaches this same function through its
    intents; a rule kept in the widget would have to be written a second time
    there, and could be forgotten.

    Which vector is active and which are ticked are left alone: editing a
    vector says nothing about what the student wants to do with it next.
    """
    vector = store.get(name)
    if vector is None or vector.locked:
        return False

    store.history.record(store.snapshot())
    store.put(replace(vector, components=components))
    _refresh_result(store)
    store.notify()
    return True


def delete_vector(store: VectorStore, name: str) -> bool:
    """Remove one vector. Returns False if there is no such vector, or if it
    is locked.

    If the deleted vector was the active one, the first remaining vector by
    name becomes active, or nothing is active if it was the last one.

    A locked vector is protected here as well as by the greyed-out button on
    its card (F-09a), for the same reason a locked vector's edit is refused
    here: this is the one place a vector can leave the scene singly, and a
    rule kept in the widget would have to be repeated by every future caller.
    `clear_all` deliberately does not check, because F-10 promises that
    clearing the scene takes locked vectors too, and says so in its prompt.
    """
    vector = store.get(name)
    if vector is None or vector.locked:
        return False

    store.history.record(store.snapshot())
    was_active = store.active_name == name
    store.remove(name)
    if was_active:
        remaining = store.names
        store.set_active(remaining[0] if remaining else None)
    _refresh_result(store)
    store.notify()
    return True


def toggle_locked(store: VectorStore, name: str) -> bool:
    """Lock or unlock a vector. Returns its new state.

    A locked vector keeps its components and cannot be deleted on its own
    (F-09a). It is otherwise a vector like any other: it can be the active
    one, it can be ticked for an operation, it shows all of its numbers, and
    Clear all still removes it.

    A toggle rather than a setter, because both things that will ask for it
    are toggles: the padlock on the card, and G5's `Thumb_Up` hold gesture
    (F-09b). Raises KeyError if there is no such vector.

    Unlike ticking, locking *is* a change to the vector, so F-19 lists it
    among the things undo must cover when that arrives in G2.8.
    """
    vector = store.get(name)
    if vector is None:
        raise KeyError(f"no vector named {name!r}")

    store.history.record(store.snapshot())
    now_locked = not vector.locked
    store.put(replace(vector, locked=now_locked))
    store.notify()
    return now_locked


def clear_all(store: VectorStore) -> None:
    """Remove every vector. The confirmation prompt is the panel's job (F-10)."""
    store.history.record(store.snapshot())
    store.clear()
    store.set_active(None)
    store.notify()


def undo(store: VectorStore) -> bool:
    """Take back the last change to the vectors (F-19). False if there is none.

    The scene as it is now is handed over so that redo can come back to it.
    Everything is put back at once and listeners hear about it once, so the
    panels and the 3D view never see a half-restored scene.
    """
    restored = store.history.undo(store.snapshot())
    if restored is None:
        return False

    store.restore(restored)
    store.notify()
    return True


def redo(store: VectorStore) -> bool:
    """Put back a change that was undone (F-19). False if there is none."""
    restored = store.history.redo(store.snapshot())
    if restored is None:
        return False

    store.restore(restored)
    store.notify()
    return True


def set_active(store: VectorStore, name: str) -> None:
    """Make `name` the active vector. Raises KeyError if it does not exist."""
    store.set_active(name)
    store.notify()


def toggle_selected(store: VectorStore, name: str) -> bool:
    """Tick or untick a vector for an operation. Returns its new state.

    Independent of the active vector (F-05a): ticking a vector does not make
    it active, and making a vector active does not tick it. Raises KeyError if
    there is no such vector.

    Ticks are deliberately left out of undo (F-19, G2.8), which covers changes
    to the vectors themselves rather than what is currently marked.
    """
    now_selected = not store.is_selected(name)
    store.set_selected(name, now_selected)
    store.notify()
    return now_selected


def toggle_components(store: VectorStore, name: str) -> bool:
    """Show or hide a vector's x, y and z parts in the 3D view. Returns the
    new state.

    Only one vector shows its components at a time: switching it on for one
    turns it off for whichever had it. Every vector resolves onto the same
    three axes, so two at once means two arrows of the same colour lying on
    the same line, with their labels in the same place.

    A display setting, not a change to the vector: F-19 keeps undo for things
    that change the vectors themselves and explicitly leaves out toggling
    components. It still goes through an action because everything that
    changes what the app is showing does, and because G5's `Victory` hold
    gesture (F-13b) will call this same function.

    Raises KeyError if there is no such vector.
    """
    now_shown = not store.is_components_shown(name)
    store.set_components_shown(name, now_shown)
    store.notify()
    return now_shown


def toggle_projections(store: VectorStore, name: str) -> bool:
    """Show or hide a vector's shadows on the XY, YZ and XZ planes (F-14).
    Returns the new state.

    Only one vector shows them at a time, like components, because three
    shadows from two vectors would overlap on the same three planes. The two
    overlays are independent of each other, so a vector can show both, and
    one vector can show its components while another shows its shadows.

    A display setting, so F-19 leaves it out of undo. It still goes through
    an action because everything that changes what the app is showing does.

    Raises KeyError if there is no such vector.
    """
    now_shown = not store.is_projections_shown(name)
    store.set_projections_shown(name, now_shown)
    store.notify()
    return now_shown


def clear_selection(store: VectorStore) -> None:
    """Untick every vector, leaving the vectors themselves alone."""
    store.clear_selection()
    store.notify()


def compute_resultant(store: VectorStore) -> Result | None:
    """Add up the ticked vectors and show the answer (F-15).

    Returns the new result, or None if fewer than two vectors are ticked,
    which is the caller's cue to leave the button disabled. Replaces whatever
    result was showing, because only one exists at a time.

    Raises `ValueError` if the sum is too large to be a number, having left
    the scene alone. The panel turns that into a message; `_refresh_result`
    handles the same failure arriving later, when a vector is edited.

    Not recorded for undo. A result is worked out from the vectors rather
    than being a change to them, and it can always be worked out again from
    the same ticks. Saving one *is* a change, and `save_result_as_vector`
    records it.
    """
    names = store.selected
    if len(names) < MIN_FOR_RESULTANT:
        return None

    result = _resultant_for(store, names)
    store.set_result(result)
    store.notify()
    return result


def save_result_as_vector(store: VectorStore) -> Vector | None:
    """Turn the temporary result into a real vector (`features.md`).

    It takes the next free letter and colour like any other vector and counts
    towards the ten. Returns None if there is no result or if ten already
    exist, which is the caller's cue to show the limit message.

    The result goes when it is saved, because the vector now standing in its
    place is the same arrow: leaving both would draw one on top of the other.

    This is the one thing about a result that undo covers (F-19), so a
    snapshot is recorded - and because the snapshot holds the result too,
    undoing the save brings the result back exactly where it was.
    """
    result = store.result
    if result is None:
        return None

    name = naming.next_free_name(store.names)
    if name is None:
        return None

    store.history.record(store.snapshot())
    vector = Vector(name=name, components=result.components, tail=result.tail)
    store.put(vector)
    store.set_active(name)
    store.set_result(None)
    store.notify()
    return vector


def clear_result(store: VectorStore) -> None:
    """Take the temporary result away."""
    store.set_result(None)
    store.notify()


def _resultant_for(store: VectorStore, names: tuple[str, ...]) -> Result:
    """Build the resultant of these vectors. Raises ValueError if it overflows."""
    vectors = [store.get(name) for name in names]
    components = resultant([v.components for v in vectors if v is not None])
    return Result(
        expression=" + ".join(names),
        components=components,
        sources=tuple(names),
    )


def _refresh_result(store: VectorStore) -> None:
    """Work the result out again, or take it away if it can no longer be shown.

    Called by every action that changes or removes a vector, before it
    notifies, so the panels and the 3D view see the vectors and the result
    agreeing with each other.

    The result goes if one of the vectors it was worked out from has been
    deleted, because a result is an answer about particular vectors and there
    is no honest answer once one of them is gone. It also goes if the sum no
    longer fits in a number, with the reason recorded for the panel - a
    result that quietly froze at its last value would be a wrong answer shown
    confidently.
    """
    result = store.result
    if result is None:
        return

    if not set(result.sources) <= set(store.names):
        store.set_result(None)
        return

    try:
        store.set_result(_resultant_for(store, result.sources))
    except ValueError:
        store.set_result(None)
        store.set_result_error(TOO_LARGE.format(expression=result.expression))

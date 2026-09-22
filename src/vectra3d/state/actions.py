"""Every allowed change to the vectors.

This is the only sanctioned way to change state. The action panel calls these
functions, and from G5 the gesture engine calls the same ones through its
intents. That is what guarantees two things the specs require: every gesture
has a panel equivalent, and every change passes through one place, which is
where undo will record its snapshots (F-19).

Each action makes its changes and then notifies the store's listeners exactly
once, so the info panel and the 3D view never redraw a half-finished change.
"""

from __future__ import annotations

from dataclasses import replace

from vectra3d.state import naming
from vectra3d.state.models import ORIGIN, Point, Vector
from vectra3d.state.store import VectorStore


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

    store.put(replace(vector, components=components))
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

    was_active = store.active_name == name
    store.remove(name)
    if was_active:
        remaining = store.names
        store.set_active(remaining[0] if remaining else None)
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

    now_locked = not vector.locked
    store.put(replace(vector, locked=now_locked))
    store.notify()
    return now_locked


def clear_all(store: VectorStore) -> None:
    """Remove every vector. The confirmation prompt is the panel's job (F-10)."""
    store.clear()
    store.set_active(None)
    store.notify()


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

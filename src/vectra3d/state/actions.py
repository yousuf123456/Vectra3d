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


def delete_vector(store: VectorStore, name: str) -> bool:
    """Remove one vector. Returns False if there is no such vector.

    If the deleted vector was the active one, the first remaining vector by
    name becomes active, or nothing is active if it was the last one.
    """
    if store.get(name) is None:
        return False

    was_active = store.active_name == name
    store.remove(name)
    if was_active:
        remaining = store.names
        store.set_active(remaining[0] if remaining else None)
    store.notify()
    return True


def clear_all(store: VectorStore) -> None:
    """Remove every vector. The confirmation prompt is the panel's job (F-10)."""
    store.clear()
    store.set_active(None)
    store.notify()


def set_active(store: VectorStore, name: str) -> None:
    """Make `name` the active vector. Raises KeyError if it does not exist."""
    store.set_active(name)
    store.notify()

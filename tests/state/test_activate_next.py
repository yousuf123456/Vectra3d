"""Making the next vector active, skipping locked ones (F-05b, F-09b)."""

from __future__ import annotations

from vectra3d.state import actions
from vectra3d.state.store import VectorStore


def store_with(count: int) -> VectorStore:
    store = VectorStore()
    for i in range(count):
        actions.create_vector(store, (1.0 + i, 0.0, 0.0))
    return store


def test_the_next_letter_becomes_active() -> None:
    store = store_with(3)  # A, B, C - C is active, as the last created
    actions.set_active(store, "A")
    assert actions.activate_next(store) == "B"
    assert store.active_name == "B"


def test_after_the_last_it_wraps_round_to_the_first() -> None:
    store = store_with(3)
    assert store.active_name == "C"
    assert actions.activate_next(store) == "A"


def test_locked_vectors_are_skipped() -> None:
    store = store_with(4)
    actions.set_active(store, "A")
    actions.toggle_locked(store, "B")
    actions.toggle_locked(store, "C")
    assert actions.activate_next(store) == "D"


def test_the_only_unlocked_vector_stays_active() -> None:
    store = store_with(3)
    actions.set_active(store, "B")
    actions.toggle_locked(store, "A")
    actions.toggle_locked(store, "C")
    assert actions.activate_next(store) == "B"


def test_with_every_vector_locked_nothing_changes() -> None:
    store = store_with(2)
    for name in store.names:
        actions.toggle_locked(store, name)
    assert actions.activate_next(store) is None
    assert store.active_name == "B"


def test_with_no_vectors_there_is_nothing_to_activate() -> None:
    assert actions.activate_next(VectorStore()) is None


def test_moving_the_highlight_is_not_an_undo_step() -> None:
    store = store_with(2)
    actions.activate_next(store)
    actions.undo(store)
    # The undo took back creating B, not the change of active vector.
    assert store.names == ("A",)

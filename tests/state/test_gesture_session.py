"""A hand gesture as one undo step (`interaction-spec.md` section 5).

A gesture changes the vectors on every frame. These tests hold the rules that
make that safe: nothing is recorded mid-gesture, a committed gesture is one
step, and a cancelled one leaves the scene exactly as it was, and no step.
"""

from __future__ import annotations

from vectra3d.state import actions
from vectra3d.state.models import ORIGIN
from vectra3d.state.store import VectorStore


def store_with_a() -> VectorStore:
    store = VectorStore()
    actions.create_vector(store, (1.0, 2.0, 3.0))
    return store


def test_a_gesture_is_in_progress_between_begin_and_end() -> None:
    store = VectorStore()
    assert not store.gesture_in_progress
    actions.begin_gesture(store)
    assert store.gesture_in_progress
    actions.commit_gesture(store)
    assert not store.gesture_in_progress

    actions.begin_gesture(store)
    actions.cancel_gesture(store)
    assert not store.gesture_in_progress


def test_nothing_is_recorded_while_a_gesture_runs() -> None:
    store = VectorStore()
    actions.begin_gesture(store)
    actions.create_vector(store, ORIGIN)
    for x in (1.0, 2.0, 3.0):
        actions.edit_vector(store, "A", (x, 0.0, 0.0))
    assert not store.history.can_undo


def test_a_committed_gesture_is_one_undo_step() -> None:
    store = store_with_a()
    actions.begin_gesture(store)
    actions.create_vector(store, ORIGIN)
    for x in (1.0, 2.0, 3.0):
        actions.edit_vector(store, "B", (x, 0.0, 0.0))
    actions.commit_gesture(store)

    assert store.get("B").components == (3.0, 0.0, 0.0)
    assert store.active_name == "B"

    # One undo takes the whole gesture back, and A is active again...
    assert actions.undo(store)
    assert store.names == ("A",)
    assert store.active_name == "A"
    # ...and the next undo is A's own creation, not a frame of the gesture.
    assert actions.undo(store)
    assert store.names == ()
    assert not store.history.can_undo


def test_redo_brings_the_whole_gesture_back() -> None:
    store = store_with_a()
    actions.begin_gesture(store)
    actions.create_vector(store, ORIGIN)
    actions.edit_vector(store, "B", (3.0, 0.0, 0.0))
    actions.commit_gesture(store)

    actions.undo(store)
    assert actions.redo(store)
    assert store.get("B").components == (3.0, 0.0, 0.0)


def test_a_gesture_that_changed_nothing_records_nothing() -> None:
    store = store_with_a()
    before = store.snapshot()

    actions.begin_gesture(store)
    actions.commit_gesture(store)

    # Still exactly one step back: A's creation.
    assert store.snapshot() == before
    actions.undo(store)
    assert not store.history.can_undo


def test_a_cancelled_gesture_puts_everything_back_and_records_nothing() -> None:
    store = store_with_a()
    actions.create_vector(store, (0.0, 4.0, 0.0))
    actions.set_active(store, "A")
    actions.toggle_selected(store, "A")
    actions.toggle_selected(store, "B")
    actions.compute_resultant(store)
    before = store.snapshot()

    actions.begin_gesture(store)
    actions.create_vector(store, ORIGIN)
    actions.edit_vector(store, "C", (5.0, 0.0, 0.0))
    actions.edit_vector(store, "A", (9.0, 9.0, 9.0))
    actions.cancel_gesture(store)

    # The vectors, the active one and the result are exactly as they were.
    assert store.snapshot() == before
    assert store.result.components == (1.0, 6.0, 3.0)
    # The two creates are still the only steps.
    actions.undo(store)
    actions.undo(store)
    assert not store.history.can_undo


def test_a_cancelled_gesture_leaves_redo_alone() -> None:
    store = store_with_a()
    actions.undo(store)
    assert store.history.can_redo

    actions.begin_gesture(store)
    actions.create_vector(store, ORIGIN)
    actions.cancel_gesture(store)

    assert store.history.can_redo


def test_ending_a_gesture_that_never_began_does_nothing() -> None:
    store = store_with_a()
    heard = []
    store.subscribe(lambda: heard.append(True))
    actions.commit_gesture(store)
    actions.cancel_gesture(store)
    assert heard == []
    assert store.names == ("A",)


def test_listeners_hear_when_a_gesture_ends() -> None:
    # The window rescales the scene on this notification, which is the
    # moment section 3 allows it.
    store = VectorStore()
    seen = []
    store.subscribe(lambda: seen.append(store.gesture_in_progress))
    actions.begin_gesture(store)
    actions.create_vector(store, ORIGIN)
    actions.edit_vector(store, "A", (1.0, 0.0, 0.0))
    actions.commit_gesture(store)
    assert seen == [True, True, False]

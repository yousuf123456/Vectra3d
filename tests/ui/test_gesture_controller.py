"""Creating a vector by hand, fed with intents (F-03, `interaction-spec.md` 6.2).

The controller has no Qt of its own, so these run without a window. The
camera is looking along +y with z up, so the screen's right is +x.
"""

from __future__ import annotations

import pytest

from vectra3d.gestures.intents import (
    BeginSteer,
    BeginTwoHand,
    Commit,
    TwoHandKind,
    UpdateTwoHand,
)
from vectra3d.state import actions, naming
from vectra3d.state.store import VectorStore
from vectra3d.ui.action_panel import LIMIT_TEXT
from vectra3d.ui.gesture_controller import GestureController

LOOKING_ALONG_Y = (0.0, 1.0, 0.0)
Z_UP = (0.0, 0.0, 1.0)

# Scale 0.25, pinch points 0.125 apart: 0.5 hs, well inside "hands together".
START = ((0.5, 0.5), (0.625, 0.5))
BEGIN = BeginTwoHand(TwoHandKind.CREATE, (0, 1), START, 0.25)
# Hand 1 pulled 1.0 right: 4.5 hs apart, (4.5 - 0.5) / 8 * 25 = 12.5 along +x.
PULLED = UpdateTwoHand(((0.5, 0.5), (1.625, 0.5)), 0.25)
# Pulled 0.03125 more than the start: 0.125 hs, 0.125 / 8 * 25 = 0.390625 long.
NUDGED = UpdateTwoHand(((0.5, 0.5), (0.65625, 0.5)), 0.25)
# Pulled only 0.001: 0.004 hs, 0.0125 long - under the 0.1 minimum.
BARELY = UpdateTwoHand(((0.5, 0.5), (0.626, 0.5)), 0.25)


def run(controller: GestureController, *intents) -> None:
    controller.apply(intents, LOOKING_ALONG_Y, Z_UP)


def test_a_vector_appears_as_soon_as_the_gesture_begins() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, BEGIN)
    assert store.names == ("A",)
    assert store.active_name == "A"
    assert store.gesture_in_progress


def test_the_vector_follows_the_hands_live() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, BEGIN, NUDGED)
    assert store.get("A").components == (0.390625, 0.0, 0.0)
    run(controller, PULLED)
    assert store.get("A").components == (12.5, 0.0, 0.0)


def test_the_label_shows_the_live_magnitude_while_creating() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, BEGIN, PULLED)
    assert controller.labels() == {"A": "|A| = 12.50"}


def test_releasing_keeps_the_vector_as_one_undo_step() -> None:
    store = VectorStore()
    actions.create_vector(store, (0.0, 3.0, 0.0))
    controller = GestureController(store)
    run(controller, BEGIN, NUDGED, PULLED, Commit())

    assert store.get("B").components == (12.5, 0.0, 0.0)
    assert store.active_name == "B"
    assert not store.gesture_in_progress
    # Back to its letter once confirmed.
    assert controller.labels() == {}

    actions.undo(store)
    assert store.names == ("A",)
    assert store.active_name == "A"


def test_the_next_vector_gets_the_lowest_free_letter() -> None:
    store = VectorStore()
    for _ in range(3):
        actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.delete_vector(store, "B")
    controller = GestureController(store)
    run(controller, BEGIN, PULLED, Commit())
    assert store.names == ("A", "B", "C")
    assert store.get("B").components == (12.5, 0.0, 0.0)


def test_a_vector_too_short_on_release_is_not_created() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, BEGIN, BARELY, Commit())
    assert store.names == ()
    assert not store.history.can_undo
    assert not store.gesture_in_progress


def test_at_ten_vectors_nothing_is_drawn_and_the_student_is_told() -> None:
    store = VectorStore()
    for _ in range(naming.MAX_VECTORS):
        actions.create_vector(store, (1.0, 0.0, 0.0))
    before = store.snapshot()
    controller = GestureController(store)

    run(controller, BEGIN, PULLED, Commit())

    assert controller.message == LIMIT_TEXT
    assert store.snapshot() == before
    assert not store.gesture_in_progress
    # No step was added: one undo takes back the tenth create, not a gesture.
    actions.undo(store)
    assert store.count == naming.MAX_VECTORS - 1


def test_the_message_goes_when_the_next_gesture_begins() -> None:
    store = VectorStore()
    for _ in range(naming.MAX_VECTORS):
        actions.create_vector(store, (1.0, 0.0, 0.0))
    controller = GestureController(store)
    run(controller, BEGIN, Commit())
    assert controller.message == LIMIT_TEXT

    run(controller, BeginSteer(0, (0.5, 0.5), 0.25))
    assert controller.message is None


# --- Resizing (F-07, `interaction-spec.md` 6.3) ---

RESIZE = BeginTwoHand(TwoHandKind.RESIZE, (0, 1), START, 0.25)
# 0.25 hs closer than the start: a stretch of -0.78125.
CLOSED = UpdateTwoHand(((0.5, 0.5), (0.5625, 0.5)), 0.25)


def store_with(*components) -> VectorStore:
    store = VectorStore()
    for value in components:
        actions.create_vector(store, value)
    return store


def test_a_resize_lengthens_the_active_vector_and_keeps_its_direction() -> None:
    # B is (3, 0, 4), 5 long. A 12.5 stretch: 17.5 long, (10.5, 0, 14).
    store = store_with((1.0, 0.0, 0.0), (3.0, 0.0, 4.0))
    controller = GestureController(store)
    run(controller, RESIZE, PULLED)

    assert store.get("B").components == pytest.approx((10.5, 0.0, 14.0))
    assert store.get("A").components == (1.0, 0.0, 0.0)
    assert store.gesture_in_progress
    assert controller.labels() == {"B": "|B| = 17.50"}


def test_closing_the_hands_shortens_it() -> None:
    # 5 - 0.78125 = 4.21875 long, along (0.6, 0, 0.8).
    store = store_with((3.0, 0.0, 4.0))
    controller = GestureController(store)
    run(controller, RESIZE, CLOSED)
    assert store.get("A").components == pytest.approx((2.53125, 0.0, 3.375))


def test_a_committed_resize_is_one_undo_step() -> None:
    store = store_with((3.0, 0.0, 4.0))
    controller = GestureController(store)
    run(controller, RESIZE, CLOSED, PULLED, Commit())

    assert not store.gesture_in_progress
    assert controller.labels() == {}
    actions.undo(store)
    assert store.get("A").components == (3.0, 0.0, 4.0)
    actions.undo(store)
    assert store.names == ()


def test_a_resize_that_changed_nothing_records_nothing() -> None:
    store = store_with((3.0, 0.0, 4.0))
    controller = GestureController(store)
    run(controller, RESIZE, Commit())
    actions.undo(store)
    assert not store.history.can_undo


def test_a_resize_shrunk_to_the_minimum_is_kept() -> None:
    # Unlike a create, a resize is never dropped on release: it cannot go
    # below the minimum magnitude, so there is nothing too short to drop.
    # Hands 8.5 hs apart closing to 0.5 hs: a stretch of -25 on a 0.5 vector.
    store = store_with((0.0, 0.5, 0.0))
    controller = GestureController(store)
    far_apart = ((0.0, 0.5), (2.125, 0.5))
    begin = BeginTwoHand(TwoHandKind.RESIZE, (0, 1), far_apart, 0.25)
    closed = UpdateTwoHand(((0.0, 0.5), (0.125, 0.5)), 0.25)
    run(controller, begin, closed, Commit())
    assert store.get("A").components == (0.0, 0.1, 0.0)


def test_a_locked_vector_is_not_resized_and_the_student_is_told() -> None:
    store = store_with((3.0, 0.0, 4.0))
    actions.toggle_locked(store, "A")
    before = store.snapshot()
    controller = GestureController(store)

    run(controller, RESIZE, PULLED, Commit())

    assert controller.message == "Vector A is locked."
    assert store.snapshot() == before
    assert not store.gesture_in_progress


def test_with_no_vector_the_student_is_told_to_create_one() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, RESIZE, PULLED, Commit())
    assert controller.message == "Create a vector first."
    assert store.names == ()
    assert not store.gesture_in_progress


def test_the_zero_vector_has_no_direction_to_resize() -> None:
    store = store_with((0.0, 0.0, 0.0))
    before = store.snapshot()
    controller = GestureController(store)
    run(controller, RESIZE, PULLED, Commit())
    assert controller.message == "Vector A has no direction to resize."
    assert store.snapshot() == before


def test_a_resize_keeps_the_result_live() -> None:
    # A + B with A resized to (10.5, 0, 14): (10.5, 1, 14).
    store = store_with((3.0, 0.0, 4.0), (0.0, 1.0, 0.0))
    actions.toggle_selected(store, "A")
    actions.toggle_selected(store, "B")
    actions.compute_resultant(store)
    actions.set_active(store, "A")
    controller = GestureController(store)

    run(controller, RESIZE, PULLED)

    assert store.result.components == pytest.approx((10.5, 1.0, 14.0))

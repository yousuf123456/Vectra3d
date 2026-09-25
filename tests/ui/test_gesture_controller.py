"""Creating a vector by hand, fed with intents (F-03, `interaction-spec.md` 6.2).

The controller has no Qt of its own, so these run without a window. The
camera is looking along +y with z up, so the screen's right is +x.
"""

from __future__ import annotations

import math

import pytest

from vectra3d.gestures.intents import (
    BeginSteer,
    BeginTwoHand,
    Cancel,
    Commit,
    TwoHandKind,
    UpdateSteer,
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


def run(controller: GestureController, *intents, now_ms: int = 0) -> None:
    controller.apply(intents, LOOKING_ALONG_Y, Z_UP, now_ms)


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


# --- Steering (F-06, `interaction-spec.md` 6.4) ---
#
# The camera looks along +y, so a vector pointing at the student is (0, -5, 0).
# Anchor at (0.5, 0.5) with a hand scale of 0.25: 1.5 hs to the right is
# 0.375 further across, full speed. Half a second of it is exactly 45 degrees.

ANCHOR = (0.5, 0.5)
STEER = BeginSteer(1, ANCHOR, 0.25)
FULL_RIGHT = UpdateSteer((0.875, 0.5), 0.25)
# 0.25 hs off the anchor: inside the 0.3 hs dead zone.
SHAKE = UpdateSteer((0.5625, 0.5), 0.25)
H = 5 * math.sqrt(0.5)


def steering_store() -> VectorStore:
    return store_with((0.0, -5.0, 0.0))


def test_a_full_push_for_half_a_second_turns_the_vector_45_degrees() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    run(controller, FULL_RIGHT, now_ms=500)

    assert store.get("A").components == pytest.approx((H, -H, 0.0))
    assert store.gesture_in_progress
    assert controller.live_name == "A"


def test_the_turn_builds_up_frame_by_frame_at_the_same_rate() -> None:
    # Ten frames of 50 ms at full speed: the same 45 degrees as one of 500.
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    for frame in range(1, 11):
        run(controller, FULL_RIGHT, now_ms=50 * frame)
    assert store.get("A").components == pytest.approx((H, -H, 0.0))


def test_steering_keeps_the_magnitude() -> None:
    store = store_with((3.0, -4.0, 0.0))
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    for frame in range(1, 40):
        run(controller, UpdateSteer((0.8, 0.3), 0.25), now_ms=33 * frame)
    assert math.hypot(*store.get("A").components) == pytest.approx(5.0, abs=1e-12)


def test_a_hand_in_the_dead_zone_changes_nothing_at_all() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    heard = []
    store.subscribe(lambda: heard.append(True))

    run(controller, SHAKE, now_ms=500)

    assert store.get("A").components == (0.0, -5.0, 0.0)
    # Not even a redraw is asked for.
    assert heard == []


def test_the_joystick_follows_the_hand_for_the_preview() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    assert controller.joystick.anchor == ANCHOR
    assert controller.joystick.point == ANCHOR

    run(controller, SHAKE, now_ms=33)
    assert controller.joystick.point == (0.5625, 0.5)
    assert controller.joystick.scale == 0.25


def test_releasing_a_steer_is_one_undo_step() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    run(controller, FULL_RIGHT, now_ms=250)
    run(controller, FULL_RIGHT, now_ms=500)
    run(controller, Commit(), now_ms=533)

    assert not store.gesture_in_progress
    assert controller.live_name is None
    assert controller.joystick is None
    actions.undo(store)
    assert store.get("A").components == (0.0, -5.0, 0.0)
    actions.undo(store)
    assert store.names == ()


def test_an_open_palm_puts_the_vector_back_exactly_and_records_nothing() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    run(controller, FULL_RIGHT, now_ms=500)
    run(controller, Cancel(), now_ms=533)

    assert store.get("A").components == (0.0, -5.0, 0.0)
    assert not store.gesture_in_progress
    assert controller.joystick is None
    # Only A's creation to undo.
    actions.undo(store)
    assert not store.history.can_undo


def test_a_locked_vector_is_not_steered_and_the_student_is_told() -> None:
    store = steering_store()
    actions.toggle_locked(store, "A")
    before = store.snapshot()
    controller = GestureController(store)

    run(controller, STEER, now_ms=0)
    run(controller, FULL_RIGHT, now_ms=500)
    run(controller, Commit(), now_ms=533)

    assert controller.message == "Vector A is locked."
    assert store.snapshot() == before
    assert controller.joystick is None


def test_steering_with_nothing_to_steer_says_why() -> None:
    controller = GestureController(VectorStore())
    run(controller, STEER)
    assert controller.message == "Create a vector first."

    controller = GestureController(store_with((0.0, 0.0, 0.0)))
    run(controller, STEER)
    assert controller.message == "Vector A has no direction to steer."


def test_steering_keeps_the_result_live() -> None:
    # A + B, with A turned 45 degrees: (H, -H, 0) + (0, 0, 1).
    store = store_with((0.0, -5.0, 0.0), (0.0, 0.0, 1.0))
    actions.toggle_selected(store, "A")
    actions.toggle_selected(store, "B")
    actions.compute_resultant(store)
    actions.set_active(store, "A")
    controller = GestureController(store)

    run(controller, STEER, now_ms=0)
    run(controller, FULL_RIGHT, now_ms=500)

    assert store.result.components == pytest.approx((H, -H, 1.0))

"""Creating a vector by hand, fed with intents (F-03, `interaction-spec.md` 6.2).

The controller has no Qt of its own, so these run without a window. The
camera is looking along +y with z up, so the screen's right is +x.
"""

from __future__ import annotations

import math

import pytest

from vectra3d import config
from vectra3d.gestures.intents import (
    BeginSteer,
    BeginTwoHand,
    Cancel,
    Commit,
    HoldTriggered,
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

    # The limit message goes. What replaces it is the steer's own news: the
    # vectors all lie on +x, so a release would snap it there (6.5).
    run(controller, BeginSteer(0, (0.5, 0.5), 0.25))
    assert controller.message == "Steering: release to snap to +x axis"


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


# --- Steering: grab and drag (F-06, `interaction-spec.md` 6.4) ---
#
# The camera looks along +y, so a vector pointing at the student is (0, -5, 0).
# The grab point is (0.5, 0.5) with a hand scale of 0.25. `hand(right, up)`
# puts the hand as far from it as turns the vector that many degrees, so
# the expected angles hold whatever the steering rate is tuned to.

ANCHOR = (0.5, 0.5)
SCALE = 0.25
STEER = BeginSteer(1, ANCHOR, SCALE)
RATE = config.STEER_DEG_PER_HS
H = 5 * math.sqrt(0.5)


def hand(right: float = 0.0, up: float = 0.0) -> UpdateSteer:
    """The steering hand, `right` and `up` degrees' worth from the grab point."""
    return UpdateSteer(
        (ANCHOR[0] + right / RATE * SCALE, ANCHOR[1] - up / RATE * SCALE), SCALE
    )


def steering_store() -> VectorStore:
    return store_with((0.0, -5.0, 0.0))


def test_dragging_turns_the_vector_by_as_much_as_the_hand_moved() -> None:
    # The first update is measured from where the pinch began, so movement
    # during the two-hand window counts.
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, hand(right=45.0))

    assert store.get("A").components == pytest.approx((H, -H, 0.0))
    assert store.gesture_in_progress
    assert controller.live_name == "A"


def test_the_turn_builds_up_frame_by_frame() -> None:
    # Five frames of 9 degrees: the same 45 degrees as one of 45.
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER)
    for frame in range(1, 6):
        run(controller, hand(right=9.0 * frame))
    assert store.get("A").components == pytest.approx((H, -H, 0.0))


def test_a_still_hand_changes_nothing_at_all() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, hand())
    assert store.get("A").components == (0.0, -5.0, 0.0)

    run(controller, hand(right=45.0))
    heard = []
    store.subscribe(lambda: heard.append(True))
    run(controller, hand(right=45.0))
    assert store.get("A").components == pytest.approx((H, -H, 0.0))
    # Not even a redraw is asked for.
    assert heard == []


def test_steering_keeps_the_magnitude() -> None:
    store = store_with((3.0, -4.0, 0.0))
    controller = GestureController(store)
    run(controller, STEER)
    for frame in range(1, 40):
        run(controller, hand(right=7.0 * math.cos(frame), up=5.0 * math.sin(frame)))
    assert math.hypot(*store.get("A").components) == pytest.approx(5.0, abs=1e-12)


def test_the_grab_follows_the_hand_for_the_preview() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER)
    assert controller.grab.anchor == ANCHOR
    assert controller.grab.point == ANCHOR

    run(controller, UpdateSteer((0.5625, 0.5), SCALE))
    assert controller.grab.anchor == ANCHOR
    assert controller.grab.point == (0.5625, 0.5)


def test_releasing_a_steer_is_one_undo_step() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, hand(right=20.0), hand(right=45.0), Commit())

    assert not store.gesture_in_progress
    assert controller.live_name is None
    assert controller.grab is None
    actions.undo(store)
    assert store.get("A").components == (0.0, -5.0, 0.0)
    actions.undo(store)
    assert store.names == ()


def test_an_open_palm_puts_the_vector_back_exactly_and_records_nothing() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, hand(right=45.0), Cancel())

    assert store.get("A").components == (0.0, -5.0, 0.0)
    assert not store.gesture_in_progress
    assert controller.grab is None
    # Only A's creation to undo.
    actions.undo(store)
    assert not store.history.can_undo


def test_a_locked_vector_is_not_steered_and_the_student_is_told() -> None:
    store = steering_store()
    actions.toggle_locked(store, "A")
    before = store.snapshot()
    controller = GestureController(store)

    run(controller, STEER, hand(right=45.0), Commit())

    assert controller.message == "Vector A is locked."
    assert store.snapshot() == before
    assert controller.grab is None


def test_steering_with_nothing_to_steer_says_why() -> None:
    controller = GestureController(VectorStore())
    run(controller, STEER)
    assert controller.message == "Create a vector first."

    controller = GestureController(store_with((0.0, 0.0, 0.0)))
    run(controller, STEER)
    assert controller.message == "Vector A has no direction to steer."


def test_up_raises_a_vector_pointing_into_the_screen() -> None:
    # The fault that replaced globe-style steering: pointing away from the
    # student, (0, 5, 0), the head rose when the hand went down.
    store = store_with((0.0, 5.0, 0.0))
    controller = GestureController(store)
    run(controller, STEER, hand(up=45.0))
    assert store.get("A").components == pytest.approx((0.0, H, H))


def test_down_lowers_a_vector_pointing_at_you_too() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, hand(up=-45.0))
    assert store.get("A").components == pytest.approx((0.0, -H, -H))


def test_right_turns_the_vector_the_same_way_round_wherever_it_points() -> None:
    # The user's request: the way a hand movement turns the vector is fixed,
    # not chosen from where it points. Right always turns it anticlockwise
    # seen from above: pointing at the student, the head goes right...
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, hand(right=45.0), Commit())
    assert store.get("A").components == pytest.approx((H, -H, 0.0))
    # ... and pointing away, it goes left, like the far side of a turntable.
    store = store_with((0.0, 5.0, 0.0))
    controller = GestureController(store)
    run(controller, STEER, hand(right=45.0))
    assert store.get("A").components == pytest.approx((-H, H, 0.0))


def test_one_long_drag_keeps_turning_the_same_way_round() -> None:
    # 180 degrees right: from +y past -x round to -y.
    store = store_with((0.0, 5.0, 0.0))
    controller = GestureController(store)
    run(controller, STEER, hand(right=90.0))
    assert store.get("A").components == pytest.approx((-5.0, 0.0, 0.0), abs=1e-12)
    run(controller, hand(right=180.0))
    assert store.get("A").components == pytest.approx((0.0, -5.0, 0.0), abs=1e-12)


def test_grabbing_again_carries_on_the_same_way_round() -> None:
    store = store_with((0.0, 5.0, 0.0))
    controller = GestureController(store)
    run(controller, STEER, hand(right=180.0), Commit())
    run(controller, STEER, hand(right=45.0))
    # From -y, 45 more anticlockwise.
    assert store.get("A").components == pytest.approx((H, -H, 0.0))


def test_the_view_does_not_change_the_way_round() -> None:
    # Looking along -y the student's right is -x; right still raises phi.
    store = store_with((0.0, 5.0, 0.0))
    controller = GestureController(store)
    controller.apply([STEER, hand(right=45.0)], (0.0, -1.0, 0.0), Z_UP)
    assert store.get("A").components == pytest.approx((-H, H, 0.0))


def test_steering_keeps_the_result_live() -> None:
    # A + B, with A turned 45 degrees: (H, -H, 0) + (0, 0, 1).
    store = store_with((0.0, -5.0, 0.0), (0.0, 0.0, 1.0))
    actions.toggle_selected(store, "A")
    actions.toggle_selected(store, "B")
    actions.compute_resultant(store)
    actions.set_active(store, "A")
    controller = GestureController(store)

    run(controller, STEER, hand(right=45.0))

    assert store.result.components == pytest.approx((H, -H, 1.0))


# --- Snapping on release (6.5) ---
#
# Vectors here lie in the XY plane, `angle` degrees round from -y towards
# +x. Dragging sideways changes only phi, so they stay in the plane and
# only the -y axis is in reach. The angle from -y is read back as
# atan2(x, -y).


def degrees_from_minus_y(components) -> float:
    return math.degrees(math.atan2(components[0], -components[1]))


def at(angle: float) -> tuple[float, float, float]:
    """5 long, `angle` degrees round from -y towards +x, in the XY plane."""
    t = math.radians(angle)
    return (5 * math.sin(t), -5 * math.cos(t), 0.0)


def near_minus_y() -> tuple[VectorStore, GestureController]:
    """Start 20 degrees off -y and drag 15.3 back: 4.7 degrees off."""
    store = store_with(at(20.0))
    controller = GestureController(store)
    run(controller, STEER, hand(right=-15.3))
    return store, controller


def test_near_an_axis_the_strip_says_where_a_release_would_snap() -> None:
    store, controller = near_minus_y()
    assert controller.message == "Steering: release to snap to -y axis"
    # Nothing snaps while the hand is moving it.
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(4.7)


def test_out_of_reach_of_an_axis_the_strip_names_only_the_plane() -> None:
    store = store_with(at(20.0))
    controller = GestureController(store)
    run(controller, STEER, hand(right=-9.0))
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(11.0)
    assert controller.message == "Steering: release to snap to XY plane"


def test_releasing_near_an_axis_lands_exactly_on_it_as_one_undo_step() -> None:
    store, controller = near_minus_y()
    run(controller, Commit())

    components = store.get("A").components
    assert components[0] == 0.0 and components[2] == 0.0
    assert components[1] == pytest.approx(-5.0)
    assert controller.message is None
    actions.undo(store)
    assert store.get("A").components == pytest.approx(at(20.0))
    actions.undo(store)
    assert store.names == ()


def test_a_snapping_release_is_reported_once_for_the_flash() -> None:
    store, controller = near_minus_y()
    assert controller.take_snapped() is None
    run(controller, Commit())
    assert controller.take_snapped() == "A"
    assert controller.take_snapped() is None


def test_releasing_out_of_reach_leaves_the_vector_where_it_is() -> None:
    store = store_with(at(20.0))
    controller = GestureController(store)
    run(controller, STEER, hand(right=-9.0), Commit())
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(11.0)
    assert controller.take_snapped() is None


def test_releasing_exactly_on_an_axis_snaps_nothing() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, hand())
    assert controller.message == "Steering: release to snap to -y axis"
    run(controller, Commit())
    assert store.get("A").components == (0.0, -5.0, 0.0)
    assert controller.take_snapped() is None


def test_a_release_snaps_both_angles_onto_an_axis() -> None:
    # 3 degrees up from +x: theta 87, phi 0 - both in reach, so the +x axis.
    store = store_with((5.0, 0.0, 0.0))
    controller = GestureController(store)
    run(controller, STEER, hand(up=3.0))
    assert store.get("A").components[2] == pytest.approx(5 * math.sin(math.radians(3.0)))
    assert controller.message == "Steering: release to snap to +x axis"
    run(controller, Commit())
    assert store.get("A").components == (5.0, 0.0, 0.0)


def test_cancelling_near_an_axis_puts_the_vector_back_and_does_not_snap() -> None:
    store, controller = near_minus_y()
    run(controller, Cancel())
    assert store.get("A").components == at(20.0)
    assert controller.message is None
    assert controller.take_snapped() is None


# --- Leaving the z axis (6.4) ---
#
# Seen along +y, the student's right is +x and towards them is -y.


def test_at_the_top_right_tips_the_head_right() -> None:
    store = store_with((0.0, 0.0, 5.0))
    controller = GestureController(store)
    run(controller, STEER, hand(right=45.0))
    assert store.get("A").components == pytest.approx((H, 0.0, H))


def test_at_the_top_down_tips_the_head_towards_the_student() -> None:
    store = store_with((0.0, 0.0, 5.0))
    controller = GestureController(store)
    run(controller, STEER, hand(up=-45.0))
    assert store.get("A").components == pytest.approx((0.0, -H, H))


def test_at_the_top_up_changes_nothing_at_all() -> None:
    store = store_with((0.0, 0.0, 5.0))
    controller = GestureController(store)
    run(controller, STEER)
    heard = []
    store.subscribe(lambda: heard.append(True))
    run(controller, hand(up=45.0))
    assert store.get("A").components == (0.0, 0.0, 5.0)
    assert heard == []


def test_once_off_the_axis_down_lowers_the_head_where_it_now_points() -> None:
    # The G5 fault: sideways at the pole changed a hidden phi and a later
    # push down went that way. Now right tips the head off towards +x, and
    # down then lowers it on that side - theta 4.5 + 45 - staying out of
    # the line of sight.
    store = store_with((0.0, 0.0, 5.0))
    controller = GestureController(store)
    run(controller, STEER, hand(right=4.5))
    run(controller, hand(right=4.5, up=-45.0))
    head = store.get("A").components
    assert head[0] > 0.0
    assert head[1] == pytest.approx(0.0, abs=1e-12)
    assert head[2] == pytest.approx(5 * math.cos(math.radians(49.5)))


def test_dragging_up_carries_on_over_the_top_and_down_the_far_side() -> None:
    # The user's report: the vector stopped at +z and only moved again once
    # the hand came back down. From 10 degrees off +z towards the student,
    # 30 up goes over the top and 20 down the far side, away from them...
    theta = math.radians(10.0)
    store = store_with((0.0, -5 * math.sin(theta), 5 * math.cos(theta)))
    controller = GestureController(store)
    run(controller, STEER, hand(up=30.0))
    far = math.radians(20.0)
    assert store.get("A").components == pytest.approx(
        (0.0, 5 * math.sin(far), 5 * math.cos(far))
    )
    # ... and keeping on up brings it level, pointing straight away.
    run(controller, hand(up=100.0))
    assert store.get("A").components == pytest.approx((0.0, 5.0, 0.0), abs=1e-12)


def test_a_full_turn_up_comes_all_the_way_round() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER)
    for degrees in range(10, 361, 10):
        run(controller, hand(up=float(degrees)))
    assert store.get("A").components == pytest.approx((0.0, -5.0, 0.0), abs=1e-12)


def test_over_the_top_right_still_turns_the_same_way_round() -> None:
    # Pointing at the student, then 180 up: over the top to pointing away.
    # Right then turns it on anticlockwise, as before it went over.
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, hand(up=180.0))
    assert store.get("A").components == pytest.approx((0.0, 5.0, 0.0), abs=1e-12)
    run(controller, hand(right=45.0, up=180.0))
    assert store.get("A").components == pytest.approx((-H, H, 0.0))


# --- A vector in the floor stays in it (6.5) ---
#
# A view like the default one, looking down at the floor from about 27
# degrees up along (-4, 3, -2.5). Found with real hands at G5.6: turning
# about the screen's axes, a sideways push tipped the vector out of the XY
# plane. Steering by angles cannot: sideways changes only phi.

RAISED = (-4.0, 3.0, -2.5)


def test_a_sideways_sweep_in_a_raised_view_stays_on_the_floor() -> None:
    store = store_with((5.0, 0.0, 0.0))
    controller = GestureController(store)
    controller.apply([STEER], RAISED, Z_UP)
    for frame in range(1, 31):  # 3 degrees a frame, 90 in all
        controller.apply([hand(right=3.0 * frame)], RAISED, Z_UP)
        assert store.get("A").components[2] == 0.0
    # Round the floor from +x to +y, and the release lands exactly on it.
    assert store.get("A").components == pytest.approx((0.0, 5.0, 0.0), abs=1e-12)
    controller.apply([Commit()], RAISED, Z_UP)
    assert store.get("A").components == (0.0, 5.0, 0.0)


def test_up_and_down_still_lift_it_off_the_floor() -> None:
    store = store_with((-4.0, 3.0, 0.0))
    controller = GestureController(store)
    controller.apply([STEER, hand(up=18.0)], RAISED, Z_UP)
    assert store.get("A").components[2] == pytest.approx(5 * math.sin(math.radians(18)))
    assert controller.message is None


# --- The gesture settings (F-20) ---


def test_the_sensitivity_sets_how_long_a_full_stretch_creates() -> None:
    # The same pull as PULLED: 4 hs more than the start, half a full stretch.
    # At 25 that is 12.5 long; at 50, 25.
    store = VectorStore()
    actions.set_sensitivity(store, 50)
    controller = GestureController(store)
    run(controller, BEGIN, PULLED)
    assert store.get("A").components == pytest.approx((25.0, 0.0, 0.0))


def test_the_sensitivity_sets_how_far_a_stretch_resizes() -> None:
    # (3, 4, 0) is 5 long; half a full stretch at 50 adds 25: 30 long.
    store = store_with((3.0, 4.0, 0.0))
    actions.set_sensitivity(store, 50)
    controller = GestureController(store)
    run(controller, RESIZE, PULLED)
    assert store.get("A").components == pytest.approx((18.0, 24.0, 0.0))


def test_with_snapping_off_a_release_near_an_axis_leaves_it_where_it_is() -> None:
    store = store_with(at(20.0))
    actions.set_snapping(store, False)
    controller = GestureController(store)
    run(controller, STEER, hand(right=-15.3))
    assert controller.message is None
    run(controller, Commit())
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(4.7)
    assert controller.take_snapped() is None


def test_turning_snapping_off_mid_drag_is_heard_at_the_release() -> None:
    store, controller = near_minus_y()
    actions.set_snapping(store, False)
    assert controller.message is None
    run(controller, Commit())
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(4.7)


# --- Hold gestures (section 7) ---

POINT = HoldTriggered("Pointing_Up")
THUMB = HoldTriggered("Thumb_Up")
VICTORY = HoldTriggered("Victory")


def test_pointing_up_makes_the_next_unlocked_vector_active() -> None:
    store = store_with((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    actions.set_active(store, "A")
    actions.toggle_locked(store, "B")
    controller = GestureController(store)
    run(controller, POINT)
    assert store.active_name == "C"
    assert controller.message is None


def test_pointing_up_with_every_vector_locked_says_so() -> None:
    store = store_with((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    actions.toggle_locked(store, "A")
    actions.toggle_locked(store, "B")
    controller = GestureController(store)
    run(controller, POINT)
    assert store.active_name == "B"
    assert controller.message == "All vectors are locked."


def test_thumb_up_locks_and_unlocks_the_active_vector_one_undo_step_each() -> None:
    store = store_with((1.0, 2.0, 3.0))
    controller = GestureController(store)
    run(controller, THUMB)
    assert store.active.locked
    run(controller, THUMB)
    assert not store.active.locked
    actions.undo(store)
    assert store.active.locked
    actions.undo(store)
    assert not store.active.locked


def test_victory_toggles_components_on_the_active_vector_even_locked() -> None:
    store = store_with((1.0, 2.0, 3.0))
    actions.toggle_locked(store, "A")
    controller = GestureController(store)
    run(controller, VICTORY)
    assert store.components_shown == "A"
    run(controller, VICTORY)
    assert store.components_shown is None


@pytest.mark.parametrize("hold", [POINT, THUMB, VICTORY])
def test_a_hold_with_no_vectors_does_nothing_and_says_why(hold) -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, hold)
    assert store.names == ()
    assert controller.message == "Create a vector first."


def test_a_hold_clears_an_earlier_refusal() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, THUMB)
    actions.create_vector(store, (1.0, 0.0, 0.0))
    run(controller, THUMB)
    assert controller.message is None
    assert store.active.locked

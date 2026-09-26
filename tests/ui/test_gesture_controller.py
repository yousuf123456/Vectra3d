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

    # The limit message goes. What replaces it is the steer's own news: the
    # vectors all lie on +x, so this one starts snapped there (6.5).
    run(controller, BeginSteer(0, (0.5, 0.5), 0.25))
    assert controller.message == "Steering, snapped to +x axis"


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


# --- Snapping while steering (6.5) ---
#
# Every turn here is about +z, so the vector stays exactly in the XY plane and
# only the -y axis can catch it. A full push turns 90 degrees a second: 0.9
# degrees every 10 ms. The angle from -y is read back as atan2(x, -y).

FULL_LEFT = UpdateSteer((0.125, 0.5), 0.25)


def degrees_from_minus_y(components) -> float:
    return math.degrees(math.atan2(components[0], -components[1]))


def on_minus_y(components) -> bool:
    """Exactly on the -y axis, at the vector's length.

    `at(20.0)` is 5.000000000000001 long, not 5, and a snap keeps the length
    it was given; "exactly on" is the other two components being zero.
    """
    return (
        components[0] == 0.0
        and components[2] == 0.0
        and components[1] == pytest.approx(-5.0)
    )


def at(angle: float) -> tuple[float, float, float]:
    """5 long, `angle` degrees round from -y towards +x, in the XY plane."""
    t = math.radians(angle)
    return (5 * math.sin(t), -5 * math.cos(t), 0.0)


def snapped_on_the_way_back() -> tuple[VectorStore, GestureController]:
    """Start 20 degrees off -y and steer back for 170 ms: 4.7 degrees off."""
    store = store_with(at(20.0))
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    run(controller, FULL_LEFT, now_ms=100)  # 11 degrees: nothing to catch it
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(11.0)
    run(controller, FULL_LEFT, now_ms=170)  # 4.7 degrees: onto the axis
    return store, controller


def test_steering_within_5_degrees_of_an_axis_puts_it_exactly_on() -> None:
    store, controller = snapped_on_the_way_back()
    assert on_minus_y(store.get("A").components)
    assert controller.message == "Steering, snapped to -y axis"


def test_the_snap_is_reported_once_for_the_flash() -> None:
    store, controller = snapped_on_the_way_back()
    assert controller.take_snap_engaged()
    assert not controller.take_snap_engaged()
    # Held on the axis for another frame: nothing new arrived.
    run(controller, FULL_LEFT, now_ms=180)
    assert not controller.take_snap_engaged()


def test_the_axis_holds_until_the_steering_is_8_degrees_away() -> None:
    store, controller = snapped_on_the_way_back()
    # On arriving, the steering starts again from the axis itself, so the
    # way back out is a full 8 degrees: 80 ms is 7.2, still held...
    run(controller, FULL_RIGHT, now_ms=250)
    assert on_minus_y(store.get("A").components)
    # ... and 100 ms is 9.0, past the release.
    run(controller, FULL_RIGHT, now_ms=270)
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(9.0)


def test_a_vector_already_on_an_axis_is_held_there_without_a_flash() -> None:
    store = steering_store()
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    assert controller.message == "Steering, snapped to -y axis"
    assert not controller.take_snap_engaged()

    heard = []
    store.subscribe(lambda: heard.append(True))
    run(controller, FULL_RIGHT, now_ms=50)  # 4.5 degrees: held
    assert store.get("A").components == (0.0, -5.0, 0.0)
    assert heard == []

    # 9 degrees: off the axis, sliding along the XY plane it already lies in.
    # A new target but no jump, so nothing to flash.
    run(controller, FULL_RIGHT, now_ms=100)
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(9.0)
    assert controller.message == "Steering, snapped to XY plane"
    assert not controller.take_snap_engaged()


def test_releasing_while_snapped_keeps_the_snapped_vector_as_one_undo_step() -> None:
    store, controller = snapped_on_the_way_back()
    run(controller, Commit(), now_ms=200)

    assert on_minus_y(store.get("A").components)
    assert controller.message is None
    assert not controller.take_snap_engaged()
    actions.undo(store)
    assert store.get("A").components == pytest.approx(at(20.0))
    actions.undo(store)
    assert store.names == ()


def test_cancelling_while_snapped_puts_the_vector_back_exactly() -> None:
    store, controller = snapped_on_the_way_back()
    run(controller, Cancel(), now_ms=200)
    assert store.get("A").components == at(20.0)
    assert controller.message is None


# --- Snap lock: steering stays within the snapped plane (6.5) ---
#
# A view like the default one, looking down at the floor from about 27
# degrees up along (-4, 3, -2.5): the screen's up is tilted from z and a sideways push alone would tip the vector
# out of the XY plane. Found with real hands at G5.6.

RAISED = (-4.0, 3.0, -2.5)


def test_a_sideways_sweep_in_a_raised_view_stays_on_the_floor() -> None:
    store = store_with((5.0, 0.0, 0.0))
    controller = GestureController(store)
    controller.apply([STEER], RAISED, Z_UP, 0)
    flashes = []
    for frame in range(1, 31):  # about 90 degrees
        controller.apply([FULL_RIGHT], RAISED, Z_UP, 33 * frame)
        assert store.get("A").components[2] == 0.0
        if controller.take_snap_engaged():
            flashes.append(controller.message)
    # Round the floor from +x to +y, flashing only on arriving at +y.
    assert store.get("A").components == pytest.approx((0.0, 5.0, 0.0))
    assert flashes == ["Steering, snapped to +y axis"]


def test_up_and_down_still_lift_it_off_the_floor() -> None:
    # (-4, 3, 0) is square to this view's right, (0.6, 0.8, 0), so a push up
    # turns it straight out of the floor: 18 degrees in 200 ms, past the 8
    # degree release.
    store = store_with((-4.0, 3.0, 0.0))
    controller = GestureController(store)
    controller.apply([STEER], RAISED, Z_UP, 0)
    controller.apply([UpdateSteer((0.5, 0.125), 0.25)], RAISED, Z_UP, 200)
    assert abs(store.get("A").components[2]) == pytest.approx(5 * math.sin(math.radians(18)))
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


def test_with_snapping_off_a_vector_near_an_axis_is_left_where_it_is() -> None:
    store = store_with(at(20.0))
    actions.set_snapping(store, False)
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    run(controller, FULL_LEFT, now_ms=170)  # 4.7 degrees off -y
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(4.7)
    assert controller.message is None
    assert not controller.take_snap_engaged()


def test_a_vector_on_an_axis_is_not_held_with_snapping_off() -> None:
    store = steering_store()
    actions.set_snapping(store, False)
    controller = GestureController(store)
    run(controller, STEER, now_ms=0)
    assert controller.message is None
    run(controller, FULL_RIGHT, now_ms=50)
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(4.5)


def test_turning_snapping_off_mid_snap_lets_go_on_the_next_frame() -> None:
    store, controller = snapped_on_the_way_back()
    actions.set_snapping(store, False)
    # Steering restarted from the axis when it snapped; 10 ms more to the
    # left carries it 0.9 degrees past -y, and nothing holds it there.
    run(controller, FULL_LEFT, now_ms=180)
    assert degrees_from_minus_y(store.get("A").components) == pytest.approx(-0.9)
    assert controller.message is None


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

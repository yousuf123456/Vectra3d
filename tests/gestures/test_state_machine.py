"""The gesture state machine, fed made-up sequences of measured hands.

Hands are written out as `TrackedHand`s directly, rather than going through
`HandMetrics`, so each test controls exactly when a pinch begins and ends.
Timings are read from `config` and each test says in its comments where on
the clock it sits, so the tests follow the spec rather than today's numbers.
"""

from __future__ import annotations

from vectra3d import config
from vectra3d.gestures.hand_frame import NO_GESTURE
from vectra3d.gestures.hand_metrics import TrackedHand
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
from vectra3d.gestures.state_machine import (
    GestureState,
    GestureStateMachine,
    HoldStatus,
    MachineOutput,
)

FRAME_MS = 33
WINDOW_MS = round(config.TWO_HAND_PINCH_WINDOW_S * 1000)
CONFIRM_MS = round(config.RELEASE_CONFIRM_S * 1000)
LOST_MS = round(config.HAND_LOST_TIMEOUT_S * 1000)
HOLD_MS = round(config.HOLD_DURATION_S * 1000)
SCALE = 0.25


def hand(
    hand_id: int,
    x: float = 0.3,
    pinching: bool = False,
    gesture: str = NO_GESTURE,
    score: float = 0.9,
) -> TrackedHand:
    return TrackedHand(
        hand_id=hand_id,
        gesture=gesture,
        gesture_score=score,
        wrist=(x, 0.8),
        scale=SCALE,
        pinch_distance_hs=0.1 if pinching else 1.0,
        pinching=pinching,
        pinch_point=(x, 0.5),
    )


def steer(machine: GestureStateMachine) -> int:
    """Hand 1 pinches at 0 ms and holds past the window. Returns the time now."""
    machine.update((hand(1, pinching=True),), 0)
    now = WINDOW_MS + 1
    assert machine.update((hand(1, pinching=True),), now).state == GestureState.STEERING
    return now


def create(machine: GestureStateMachine) -> None:
    """Hands 1 and 2 pinch together at 0 ms, 0.05 apart: a create."""
    both = (hand(1, x=0.30, pinching=True), hand(2, x=0.35, pinching=True))
    assert machine.update(both, 0).state == GestureState.CREATING


# --- Idle ---


def test_no_hands_is_idle_and_asks_for_nothing() -> None:
    assert GestureStateMachine().update((), 0) == MachineOutput(
        GestureState.IDLE, (), None
    )


def test_an_open_palm_in_idle_does_nothing() -> None:
    output = GestureStateMachine().update((hand(1, gesture="Open_Palm"),), 0)

    assert output == MachineOutput(GestureState.IDLE, (), None)


# --- One pinch: the two-hand window, then steering ---


def test_one_pinch_waits_and_begins_nothing_yet() -> None:
    output = GestureStateMachine().update((hand(1, pinching=True),), 0)

    assert output == MachineOutput(GestureState.WAITING, (), None)


def test_still_waiting_at_the_very_end_of_the_window() -> None:
    machine = GestureStateMachine()
    machine.update((hand(1, pinching=True),), 0)

    output = machine.update((hand(1, pinching=True),), WINDOW_MS)

    assert output.state == GestureState.WAITING
    assert output.intents == ()


def test_steering_begins_once_the_window_has_passed_anchored_where_it_began() -> None:
    # Pinched at x 0.30, and drifted to 0.34 while the window ran out. The
    # anchor is where the pinch began (section 6.4), so the drift already
    # counts as joystick deflection.
    machine = GestureStateMachine()
    machine.update((hand(1, x=0.30, pinching=True),), 0)
    machine.update((hand(1, x=0.32, pinching=True),), WINDOW_MS // 2)

    output = machine.update((hand(1, x=0.34, pinching=True),), WINDOW_MS + 1)

    assert output.state == GestureState.STEERING
    assert output.intents == (
        BeginSteer(hand_id=1, anchor=(0.30, 0.5), scale=SCALE),
        UpdateSteer(pinch_point=(0.34, 0.5), scale=SCALE),
    )


def test_steering_reports_the_hand_every_frame() -> None:
    machine = GestureStateMachine()
    now = steer(machine)

    output = machine.update((hand(1, x=0.4, pinching=True),), now + FRAME_MS)

    assert output.intents == (UpdateSteer(pinch_point=(0.4, 0.5), scale=SCALE),)


def test_letting_go_before_the_window_ends_begins_nothing() -> None:
    machine = GestureStateMachine()
    machine.update((hand(1, pinching=True),), 0)

    output = machine.update((hand(1),), FRAME_MS)

    assert output == MachineOutput(GestureState.IDLE, (), None)


# --- Two hands ---


def test_a_second_pinch_at_the_end_of_the_window_makes_a_two_hand_gesture() -> None:
    machine = GestureStateMachine()
    machine.update((hand(1, x=0.30, pinching=True),), 0)

    output = machine.update(
        (hand(1, x=0.30, pinching=True), hand(2, x=0.35, pinching=True)), WINDOW_MS
    )

    assert output.state == GestureState.CREATING
    assert output.intents == (
        BeginTwoHand(TwoHandKind.CREATE, (1, 2), ((0.30, 0.5), (0.35, 0.5)), SCALE),
    )


def test_both_hands_pinching_in_the_same_frame_is_a_two_hand_gesture() -> None:
    machine = GestureStateMachine()

    create(machine)


def test_a_second_pinch_after_the_window_is_ignored_while_steering() -> None:
    machine = GestureStateMachine()
    now = steer(machine)

    output = machine.update(
        (hand(1, pinching=True), hand(2, x=0.6, pinching=True)), now + FRAME_MS
    )

    assert output.state == GestureState.STEERING
    assert output.intents == (UpdateSteer(pinch_point=(0.3, 0.5), scale=SCALE),)


def test_hands_closer_than_one_hand_scale_create() -> None:
    # 0.24 apart with hands 0.25 across: 0.96 hs, under the 1.0 hs line.
    machine = GestureStateMachine()
    close = SCALE * config.HANDS_TOGETHER_HS - 0.01

    output = machine.update(
        (hand(1, x=0.25, pinching=True), hand(2, x=0.25 + close, pinching=True)), 0
    )

    assert output.state == GestureState.CREATING
    assert output.intents[0].kind == TwoHandKind.CREATE


def test_hands_exactly_one_hand_scale_apart_resize() -> None:
    # 0.25 apart with hands 0.25 across: exactly 1.0 hs, which section 6.3
    # calls "1.0 hs or more" - a resize. Both numbers are exact in binary.
    machine = GestureStateMachine()
    apart = SCALE * config.HANDS_TOGETHER_HS

    output = machine.update(
        (hand(1, x=0.25, pinching=True), hand(2, x=0.25 + apart, pinching=True)), 0
    )

    assert output.state == GestureState.RESIZING
    assert output.intents[0].kind == TwoHandKind.RESIZE


def test_a_two_hand_gesture_reports_both_hands_every_frame() -> None:
    machine = GestureStateMachine()
    create(machine)

    output = machine.update(
        (hand(1, x=0.20, pinching=True), hand(2, x=0.45, pinching=True)), FRAME_MS
    )

    assert output.intents == (UpdateTwoHand(((0.20, 0.5), (0.45, 0.5)), SCALE),)


# --- Releasing and committing ---


def test_a_released_pinch_waits_the_confirm_window_then_commits() -> None:
    machine = GestureStateMachine()
    create(machine)
    released = FRAME_MS
    open_hand = (hand(1, x=0.30, pinching=True), hand(2, x=0.35))

    first = machine.update(open_hand, released)
    almost = machine.update(open_hand, released + CONFIRM_MS - 1)
    done = machine.update(open_hand, released + CONFIRM_MS)

    # Frozen while it waits: no updates, no commit yet.
    assert first == MachineOutput(GestureState.RELEASING, (), None)
    assert almost == MachineOutput(GestureState.RELEASING, (), None)
    assert done == MachineOutput(GestureState.IDLE, (Commit(),), None)


def test_steering_releases_through_the_same_window() -> None:
    machine = GestureStateMachine()
    now = steer(machine)
    machine.update((hand(1),), now + FRAME_MS)

    output = machine.update((hand(1),), now + FRAME_MS + CONFIRM_MS)

    assert output.intents == (Commit(),)


def test_a_pinch_still_held_after_a_gesture_ends_starts_nothing() -> None:
    # Hand 1 lets go of a create; hand 2 keeps pinching. It must not start
    # steering the vector that was just made.
    machine = GestureStateMachine()
    create(machine)
    still = (hand(1, x=0.30), hand(2, x=0.35, pinching=True))
    machine.update(still, FRAME_MS)
    machine.update(still, FRAME_MS + CONFIRM_MS)

    later = FRAME_MS + CONFIRM_MS + WINDOW_MS + 100
    output = machine.update(still, later)

    assert output == MachineOutput(GestureState.IDLE, (), None)


def test_a_hand_that_lets_go_and_pinches_again_starts_afresh() -> None:
    machine = GestureStateMachine()
    create(machine)
    still = (hand(1, x=0.30), hand(2, x=0.35, pinching=True))
    machine.update(still, FRAME_MS)
    ended = FRAME_MS + CONFIRM_MS
    machine.update(still, ended)

    machine.update((hand(1, x=0.30), hand(2, x=0.35)), ended + FRAME_MS)
    output = machine.update(
        (hand(1, x=0.30), hand(2, x=0.35, pinching=True)), ended + 2 * FRAME_MS
    )

    assert output.state == GestureState.WAITING


def test_the_ignored_second_pinch_starts_nothing_when_steering_ends() -> None:
    machine = GestureStateMachine()
    now = steer(machine)
    both = (hand(1, pinching=True), hand(2, x=0.6, pinching=True))
    machine.update(both, now + FRAME_MS)
    only_two = (hand(1), hand(2, x=0.6, pinching=True))
    machine.update(only_two, now + 2 * FRAME_MS)
    machine.update(only_two, now + 2 * FRAME_MS + CONFIRM_MS)

    output = machine.update(only_two, now + 2 * FRAME_MS + CONFIRM_MS + 500)

    assert output == MachineOutput(GestureState.IDLE, (), None)


# --- Cancelling with an open palm ---


def test_an_open_palm_in_the_confirm_window_cancels() -> None:
    # The usual way to cancel a create: one hand opens (a release), and a
    # moment later MediaPipe calls it an open palm.
    machine = GestureStateMachine()
    create(machine)
    machine.update((hand(1, x=0.30, pinching=True), hand(2, x=0.35)), FRAME_MS)

    output = machine.update(
        (hand(1, x=0.30, pinching=True), hand(2, x=0.35, gesture="Open_Palm")),
        FRAME_MS + CONFIRM_MS - 1,
    )

    assert output == MachineOutput(GestureState.IDLE, (Cancel(),), None)


def test_the_free_hand_cancels_steering_at_once() -> None:
    machine = GestureStateMachine()
    now = steer(machine)

    output = machine.update(
        (hand(1, pinching=True), hand(2, x=0.6, gesture="Open_Palm")), now + FRAME_MS
    )

    assert output == MachineOutput(GestureState.IDLE, (Cancel(),), None)


def test_an_open_palm_after_the_commit_changes_nothing() -> None:
    machine = GestureStateMachine()
    create(machine)
    open_hand = (hand(1, x=0.30, pinching=True), hand(2, x=0.35))
    machine.update(open_hand, FRAME_MS)
    machine.update(open_hand, FRAME_MS + CONFIRM_MS)

    output = machine.update(
        (hand(1, x=0.30), hand(2, x=0.35, gesture="Open_Palm")),
        FRAME_MS + CONFIRM_MS + FRAME_MS,
    )

    assert output == MachineOutput(GestureState.IDLE, (), None)


def test_a_pinching_hand_read_as_an_open_palm_does_not_cancel_a_create() -> None:
    # Measured with real hands: a pinch with the other fingers stretched out
    # is often classified as Open_Palm. Both hands are pinching here, so
    # neither can be showing a real palm.
    machine = GestureStateMachine()
    create(machine)

    output = machine.update(
        (
            hand(1, x=0.30, pinching=True, gesture="Open_Palm"),
            hand(2, x=0.35, pinching=True),
        ),
        FRAME_MS,
    )

    assert output.state == GestureState.CREATING
    assert output.intents == (UpdateTwoHand(((0.30, 0.5), (0.35, 0.5)), SCALE),)


def test_the_steering_hand_read_as_an_open_palm_does_not_cancel() -> None:
    machine = GestureStateMachine()
    now = steer(machine)

    output = machine.update(
        (hand(1, pinching=True, gesture="Open_Palm"),), now + FRAME_MS
    )

    assert output.state == GestureState.STEERING


def test_an_open_palm_while_waiting_does_nothing() -> None:
    # Nothing has begun, so there is nothing to cancel.
    machine = GestureStateMachine()
    machine.update((hand(1, pinching=True),), 0)

    output = machine.update(
        (hand(1, pinching=True), hand(2, x=0.6, gesture="Open_Palm")), FRAME_MS
    )

    assert output == MachineOutput(GestureState.WAITING, (), None)


# --- Losing a hand ---


def test_a_steering_hand_missing_for_the_timeout_is_paused_not_lost() -> None:
    machine = GestureStateMachine()
    now = steer(machine)

    gap = machine.update((), now + LOST_MS)
    back = machine.update((hand(1, x=0.4, pinching=True),), now + LOST_MS + FRAME_MS)

    # Section 4.4: lost only after *more* than the timeout.
    assert gap == MachineOutput(GestureState.STEERING, (), None)
    assert back.intents == (UpdateSteer(pinch_point=(0.4, 0.5), scale=SCALE),)


def test_a_steering_hand_lost_for_longer_commits_at_once() -> None:
    # A normal release, not a cancel - and not held in the confirm window,
    # since only an open palm can turn a release into a cancel.
    machine = GestureStateMachine()
    now = steer(machine)
    machine.update((), now + FRAME_MS)

    output = machine.update((), now + LOST_MS + 1)

    assert output == MachineOutput(GestureState.IDLE, (Commit(),), None)


def test_one_hand_of_a_two_hand_gesture_lost_commits() -> None:
    machine = GestureStateMachine()
    create(machine)
    only_one = (hand(1, x=0.30, pinching=True),)
    machine.update(only_one, FRAME_MS)

    output = machine.update(only_one, LOST_MS + 1)

    assert output == MachineOutput(GestureState.IDLE, (Commit(),), None)


def test_a_first_pinch_that_vanishes_while_waiting_begins_nothing() -> None:
    machine = GestureStateMachine()
    machine.update((hand(1, pinching=True),), 0)

    output = machine.update((), FRAME_MS)

    assert output == MachineOutput(GestureState.IDLE, (), None)


# --- Hold gestures ---


def test_a_hold_fills_up_and_triggers_once_at_its_duration() -> None:
    machine = GestureStateMachine()
    thumb = (hand(1, gesture="Thumb_Up"),)

    start = machine.update(thumb, 0)
    half = machine.update(thumb, HOLD_MS // 2)
    just_short = machine.update(thumb, HOLD_MS - 1)
    fired = machine.update(thumb, HOLD_MS)

    assert start == MachineOutput(GestureState.HOLDING, (), HoldStatus("Thumb_Up", 0.0))
    assert half.hold == HoldStatus("Thumb_Up", 0.5)
    assert just_short.state == GestureState.HOLDING
    assert fired == MachineOutput(GestureState.IDLE, (HoldTriggered("Thumb_Up"),), None)


def test_a_hold_does_not_trigger_again_until_the_hand_changes_shape() -> None:
    machine = GestureStateMachine()
    thumb = (hand(1, gesture="Thumb_Up"),)
    machine.update(thumb, 0)
    machine.update(thumb, HOLD_MS)

    # Still showing the thumb, long after: nothing.
    kept = [machine.update(thumb, HOLD_MS + i * 100) for i in range(1, 11)]
    # A different shape for one frame re-arms it.
    machine.update((hand(1),), HOLD_MS + 1100)
    again = machine.update(thumb, HOLD_MS + 1200)

    assert all(out == MachineOutput(GestureState.IDLE, (), None) for out in kept)
    assert again.state == GestureState.HOLDING


def test_switching_straight_to_another_hold_gesture_counts_as_a_new_shape() -> None:
    machine = GestureStateMachine()
    machine.update((hand(1, gesture="Thumb_Up"),), 0)
    machine.update((hand(1, gesture="Thumb_Up"),), HOLD_MS)

    output = machine.update((hand(1, gesture="Victory"),), HOLD_MS + FRAME_MS)

    assert output.hold == HoldStatus("Victory", 0.0)


def test_a_hold_below_the_confidence_never_starts() -> None:
    machine = GestureStateMachine()
    weak = (hand(1, gesture="Thumb_Up", score=config.HOLD_CONFIDENCE - 0.01),)

    outputs = [machine.update(weak, i * 100) for i in range(10)]

    assert all(out == MachineOutput(GestureState.IDLE, (), None) for out in outputs)


def test_a_confidence_dip_breaks_the_hold_and_it_starts_over() -> None:
    machine = GestureStateMachine()
    thumb = (hand(1, gesture="Thumb_Up"),)
    machine.update(thumb, 0)
    machine.update(thumb, HOLD_MS - 100)

    dip = machine.update(
        (hand(1, gesture="Thumb_Up", score=config.HOLD_CONFIDENCE - 0.01),), HOLD_MS - 50
    )
    restart = machine.update(thumb, HOLD_MS)

    assert dip == MachineOutput(GestureState.IDLE, (), None)
    assert restart.hold == HoldStatus("Thumb_Up", 0.0)


def test_a_pinch_beginning_during_a_hold_abandons_it() -> None:
    machine = GestureStateMachine()
    machine.update((hand(1, gesture="Thumb_Up"), hand(2, x=0.6)), 0)

    output = machine.update(
        (hand(1, gesture="Thumb_Up"), hand(2, x=0.6, pinching=True)), FRAME_MS
    )

    assert output == MachineOutput(GestureState.WAITING, (), None)


def test_hold_gestures_are_ignored_during_a_pinch_gesture() -> None:
    machine = GestureStateMachine()
    now = steer(machine)
    both = (hand(1, pinching=True), hand(2, x=0.6, gesture="Thumb_Up"))

    outputs = [machine.update(both, now + i * 100) for i in range(1, 11)]

    assert all(out.state == GestureState.STEERING for out in outputs)
    assert all(out.hold is None for out in outputs)
    assert not any(
        isinstance(intent, HoldTriggered) for out in outputs for intent in out.intents
    )


def test_open_palm_is_not_a_hold_gesture() -> None:
    output = GestureStateMachine().update((hand(1, gesture="Open_Palm"),), 0)

    assert output.hold is None

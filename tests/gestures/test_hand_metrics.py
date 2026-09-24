"""Hand metrics: hand scale, pinch detection, smoothing, and telling hands apart.

Everything here runs on made-up hands; no camera and no MediaPipe. Expected
values are worked out by hand in the comments.

Pinch thresholds are read from `config` rather than written out, for the same
reason as `test_config.py`: they are meant to be retuned after real testing,
and a test that repeated them would have to be edited alongside every change.
"""

from __future__ import annotations

import random
import statistics

import pytest

from vectra3d import config
from vectra3d.gestures.hand_frame import NO_GESTURE, Hand, HandFrame
from vectra3d.gestures.hand_metrics import (
    HandMetrics,
    OneEuroFilter,
    average_scale,
    hand_scale,
    next_pinch,
    pinch_distance_hs,
    pinch_point,
    to_picture_units,
)

ASPECT = 4 / 3
FRAME_MS = 33

# Distances either side of, and between, the two pinch thresholds.
BELOW_START = config.PINCH_START_HS - 0.01
BETWEEN = (config.PINCH_START_HS + config.PINCH_END_HS) / 2
ABOVE_END = config.PINCH_END_HS + 0.01

# The filter authors' defaults, written out so the filter's own tests do not
# move when the app's smoothing is retuned.
AUTHORS_MIN_CUTOFF_HZ = 1.0
AUTHORS_DERIVATIVE_CUTOFF_HZ = 1.0


def upright_hand(
    wrist: tuple[float, float] = (0.5, 0.8),
    gap_hs: float = 1.0,
    gesture: str = NO_GESTURE,
) -> Hand:
    """A hand pointing straight up, 1 hs = 0.2 picture heights.

    Every point that matters shares one x, so the picture's shape plays no
    part and the numbers stay easy: the middle-finger base is 0.2 above the
    wrist, and the index tip sits `gap_hs` hand-scales above the thumb tip.
    """
    x, y = wrist
    points = [wrist] * 21
    points[9] = (x, y - 0.2)
    points[4] = (x, y - 0.4)
    points[8] = (x, y - 0.4 - gap_hs * 0.2)
    return Hand(landmarks=tuple(points), gesture=gesture, gesture_score=0.9)


def frame(*hands: Hand, time_ms: int = 0) -> HandFrame:
    return HandFrame(hands=hands, timestamp_ms=time_ms, aspect=ASPECT)


def authors_filter(beta: float = 0.0) -> OneEuroFilter:
    return OneEuroFilter(AUTHORS_MIN_CUTOFF_HZ, beta, AUTHORS_DERIVATIVE_CUTOFF_HZ)


# --- The picture's shape ---


def test_x_is_stretched_by_the_aspect_and_y_is_left_alone() -> None:
    # 0.3 of a 4:3 picture's width is 0.3 * 4/3 = 0.4 of its height.
    assert to_picture_units((0.3, 0.6), ASPECT) == pytest.approx((0.4, 0.6))


def test_a_hand_measures_the_same_upright_or_sideways() -> None:
    # Upright: the middle-finger base 0.2 above the wrist - 0.2 heights.
    # Sideways: 0.15 across. On a 4:3 picture that is 0.15 * 4/3 = 0.2 heights,
    # the same hand. Measured in raw 0-1 units it would read 0.15, a quarter
    # smaller, just for being turned.
    upright = [(0.5, 0.5)] * 21
    upright[9] = (0.5, 0.3)
    sideways = [(0.5, 0.5)] * 21
    sideways[9] = (0.65, 0.5)

    first = HandMetrics().update(frame(Hand(tuple(upright), NO_GESTURE, 0.9)))[0]
    second = HandMetrics().update(frame(Hand(tuple(sideways), NO_GESTURE, 0.9)))[0]

    assert first.scale == pytest.approx(0.2)
    assert second.scale == pytest.approx(0.2)


# --- Hand scale and pinch distance ---


def test_hand_scale_is_the_wrist_to_the_middle_finger_base() -> None:
    # A 3-4-5 triangle: 0.03 across and 0.04 down is 0.05.
    assert hand_scale((0.1, 0.1), (0.13, 0.14)) == pytest.approx(0.05)


def test_pinch_distance_is_measured_in_hand_scales() -> None:
    # Fingertips 0.05 apart (3-4-5 again) on a hand 0.25 across: 0.2 hs.
    assert pinch_distance_hs((0.0, 0.0), (0.03, 0.04), 0.25) == pytest.approx(0.2)


def test_pinch_distance_does_not_change_with_distance_from_the_camera() -> None:
    # The same hand twice as close: fingertips twice as far apart on screen,
    # and the hand twice as big, so the same 0.2 hs.
    near = pinch_distance_hs((0.0, 0.0), (0.06, 0.08), 0.5)
    far = pinch_distance_hs((0.0, 0.0), (0.03, 0.04), 0.25)

    assert near == pytest.approx(far)


def test_a_hand_of_no_size_has_no_pinch_distance() -> None:
    assert pinch_distance_hs((0.1, 0.1), (0.2, 0.2), 0.0) is None


def test_the_pinch_point_is_halfway_between_the_fingertips() -> None:
    assert pinch_point((0.2, 0.4), (0.4, 0.8)) == pytest.approx((0.3, 0.6))


# --- Pinch hysteresis ---


def test_a_pinch_starts_below_the_start_threshold_and_ends_above_the_end() -> None:
    # Closing, hovering, opening a little, opening wide, hovering again.
    distances = [BETWEEN, BELOW_START, BETWEEN, ABOVE_END, BETWEEN]
    states = []
    pinching = False
    for distance in distances:
        pinching = next_pinch(pinching, distance)
        states.append(pinching)

    # Between the two thresholds the hand keeps whatever it had: off at the
    # start, on after closing, off again after opening wide.
    assert states == [False, True, True, False, False]


def test_the_thresholds_themselves_do_not_change_the_state() -> None:
    # "Starts when it falls below", "ends when it rises above": landing
    # exactly on either threshold is neither.
    assert next_pinch(False, config.PINCH_START_HS) is False
    assert next_pinch(True, config.PINCH_END_HS) is True


def test_a_hand_with_no_pinch_distance_is_not_pinching() -> None:
    assert next_pinch(True, None) is False


def test_a_hand_of_no_size_is_measured_as_not_pinching() -> None:
    # Every point in one place: no scale, so nothing to divide by.
    flat = Hand(landmarks=((0.5, 0.5),) * 21, gesture=NO_GESTURE, gesture_score=0.9)

    hand = HandMetrics().update(frame(flat))[0]

    assert hand.pinch_distance_hs is None
    assert hand.pinching is False


# --- The One Euro filter ---


def test_the_first_sample_passes_through_unchanged() -> None:
    assert authors_filter()(0.7, 0.0) == 0.7


def test_a_value_that_does_not_move_stays_exactly_where_it_is() -> None:
    smooth = authors_filter()
    outputs = [smooth(0.42, i / 30) for i in range(30)]

    assert outputs == [0.42] * 30


def test_one_step_moves_the_filter_by_the_textbook_factor() -> None:
    # At rest the cutoff is 1 Hz, so the time constant is 1/(2 pi) s. One frame
    # later (1/30 s) the filter moves 1 / (1 + (1/(2 pi)) / (1/30)) of the way,
    # which is 2 pi / (2 pi + 30) = 6.28319 / 36.28319 = 0.17317 of the way
    # from 0 to 1.
    smooth = authors_filter()
    smooth(0.0, 0.0)

    assert smooth(1.0, 1 / 30) == pytest.approx(0.17317, abs=1e-5)


def test_the_filter_uses_the_real_time_between_samples() -> None:
    # A slow frame, 0.1 s after the last: 2 pi * 0.1 / (2 pi * 0.1 + 1) = 0.38586.
    # More time has passed, so the filter trusts the new value more.
    smooth = authors_filter()
    smooth(0.0, 0.0)

    assert smooth(1.0, 0.1) == pytest.approx(0.38586, abs=1e-5)


def test_beta_makes_the_filter_follow_fast_movement_more_closely() -> None:
    # The same jump with beta = 1. The raw speed is 1 / (1/30) = 30 per second;
    # filtered at 1 Hz it is 30 * 0.17317 = 5.1951. The cutoff rises to
    # 1 + 5.1951 = 6.1951 Hz, so the filter moves
    # 2 pi * 6.1951 / (2 pi * 6.1951 + 30) = 38.925 / 68.925 = 0.56474 of the
    # way, against 0.17317 with beta at 0.
    smooth = authors_filter(beta=1.0)
    smooth(0.0, 0.0)

    assert smooth(1.0, 1 / 30) == pytest.approx(0.56474, abs=1e-5)


def test_jitter_around_a_still_point_is_smoothed_away() -> None:
    # A hand held still, reported with random shake of 0.005 picture heights,
    # 30 times a second for 10 seconds. Seeded, so the run is the same every
    # time. With the filter moving 0.17317 of the way each frame, the shake
    # left over is sqrt(0.17317 / (2 - 0.17317)) = 0.31 of the original, so
    # well under half of it survives - while the average stays where the
    # hand is.
    shake = random.Random(20260924)
    raw = [0.5 + shake.gauss(0.0, 0.005) for _ in range(300)]
    smooth = authors_filter()
    smoothed = [smooth(value, i / 30) for i, value in enumerate(raw)]

    # The first second is left out while the filter settles.
    raw_spread = statistics.pstdev(raw[30:])
    smoothed_spread = statistics.pstdev(smoothed[30:])
    assert smoothed_spread < 0.4 * raw_spread
    assert statistics.fmean(smoothed[30:]) == pytest.approx(0.5, abs=0.002)


# --- Measuring hands frame by frame ---


def test_a_hand_is_measured_in_picture_units() -> None:
    hand = HandMetrics().update(frame(upright_hand(gap_hs=0.5, gesture="Victory")))[0]

    assert hand.gesture == "Victory"
    assert hand.gesture_score == 0.9
    assert hand.scale == pytest.approx(0.2)
    assert hand.pinch_distance_hs == pytest.approx(0.5)
    # The wrist's x of 0.5 is 0.5 * 4/3 of the picture's height across.
    assert hand.wrist == pytest.approx((0.5 * ASPECT, 0.8))
    # Thumb tip at y 0.4, index tip 0.5 hs = 0.1 above it: halfway is 0.35.
    assert hand.pinch_point == pytest.approx((0.5 * ASPECT, 0.35))


def test_a_hand_that_arrives_pinched_is_pinching() -> None:
    hand = HandMetrics().update(frame(upright_hand(gap_hs=BELOW_START)))[0]

    assert hand.pinching is True


def test_a_pinch_is_remembered_while_the_fingers_hover_between_thresholds() -> None:
    metrics = HandMetrics()
    metrics.update(frame(upright_hand(gap_hs=BELOW_START)))

    hand = metrics.update(frame(upright_hand(gap_hs=BETWEEN), time_ms=FRAME_MS))[0]

    assert hand.pinching is True


def test_a_pinch_ends_once_the_fingers_open_wide() -> None:
    metrics = HandMetrics()
    metrics.update(frame(upright_hand(gap_hs=BELOW_START)))

    # Smoothing makes the fingertips take a few frames to catch up.
    for i in range(1, 31):
        hand = metrics.update(frame(upright_hand(gap_hs=1.0), time_ms=i * FRAME_MS))[0]

    assert hand.pinching is False


def test_positions_are_smoothed_between_frames() -> None:
    metrics = HandMetrics()
    metrics.update(frame(upright_hand(wrist=(0.3, 0.8))))

    hand = metrics.update(frame(upright_hand(wrist=(0.36, 0.8)), time_ms=FRAME_MS))[0]

    # It has moved toward the new place, not all the way there.
    assert 0.3 * ASPECT < hand.wrist[0] < 0.36 * ASPECT


# --- Telling hands apart ---


def test_hands_keep_their_ids_when_they_arrive_in_the_other_order() -> None:
    metrics = HandMetrics()
    left, right = metrics.update(
        frame(upright_hand(wrist=(0.2, 0.8)), upright_hand(wrist=(0.8, 0.8)))
    )

    # Next frame: both have moved a little, and MediaPipe lists them swapped.
    first, second = metrics.update(
        frame(
            upright_hand(wrist=(0.78, 0.8)),
            upright_hand(wrist=(0.22, 0.8)),
            time_ms=FRAME_MS,
        )
    )

    assert first.hand_id == right.hand_id
    assert second.hand_id == left.hand_id
    assert left.hand_id != right.hand_id


def test_a_second_hand_gets_a_new_id_and_the_first_keeps_its_own() -> None:
    metrics = HandMetrics()
    (only,) = metrics.update(frame(upright_hand(wrist=(0.3, 0.8))))

    newcomer, original = metrics.update(
        frame(
            upright_hand(wrist=(0.7, 0.8)),
            upright_hand(wrist=(0.31, 0.8)),
            time_ms=FRAME_MS,
        )
    )

    assert original.hand_id == only.hand_id
    assert newcomer.hand_id != only.hand_id


LOST_MS = round(config.HAND_LOST_TIMEOUT_S * 1000)


def test_a_hand_back_within_the_timeout_is_the_same_hand_still_pinching() -> None:
    # Pinched, then out of view for exactly the hand-lost timeout, then back
    # with the fingers between the two thresholds. Section 4.4 says a hand is
    # lost only after *more* than the timeout, so this one is remembered - and
    # being remembered as pinching, it still is.
    metrics = HandMetrics()
    (before,) = metrics.update(frame(upright_hand(gap_hs=BELOW_START)))
    metrics.update(frame(time_ms=FRAME_MS))

    (after,) = metrics.update(frame(upright_hand(gap_hs=BETWEEN), time_ms=LOST_MS))

    assert after.hand_id == before.hand_id
    assert after.pinching is True


def test_a_hand_back_after_the_timeout_is_a_new_hand() -> None:
    # The same, one millisecond later. A fresh hand between the thresholds
    # has never closed below the start threshold, so it is not pinching.
    metrics = HandMetrics()
    (before,) = metrics.update(frame(upright_hand(gap_hs=BELOW_START)))
    metrics.update(frame(time_ms=FRAME_MS))

    (after,) = metrics.update(frame(upright_hand(gap_hs=BETWEEN), time_ms=LOST_MS + 1))

    assert after.hand_id != before.hand_id
    assert after.pinching is False


def test_a_slow_frame_does_not_lose_a_hand_that_was_in_view() -> None:
    # The hand is in both frames, but the second arrives well past the
    # timeout - the tracker stalled. It was never missing, so it is the same
    # hand, still pinching.
    metrics = HandMetrics()
    (before,) = metrics.update(frame(upright_hand(gap_hs=BELOW_START)))

    (after,) = metrics.update(frame(upright_hand(gap_hs=BETWEEN), time_ms=3 * LOST_MS))

    assert after.hand_id == before.hand_id
    assert after.pinching is True


def test_a_missing_hand_is_not_returned() -> None:
    metrics = HandMetrics()
    metrics.update(frame(upright_hand()))

    assert metrics.update(frame(time_ms=FRAME_MS)) == ()


def test_average_scale_is_the_mean_of_two_hands() -> None:
    # One hand 0.2 across (upright_hand), one 0.3: 0.25.
    small = HandMetrics().update(frame(upright_hand()))[0]
    big_points = [(0.5, 0.8)] * 21
    big_points[9] = (0.5, 0.5)
    big = HandMetrics().update(frame(Hand(tuple(big_points), NO_GESTURE, 0.9)))[0]

    assert average_scale(small, big) == pytest.approx(0.25)


def test_no_hands_gives_nothing() -> None:
    assert HandMetrics().update(frame()) == ()

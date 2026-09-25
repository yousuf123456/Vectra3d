"""Hand positions into vectors (`interaction-spec.md` sections 6.1 and 6.2).

Every expected value is worked out by hand. Points are in picture-height
units, as the metrics give them; distances are chosen to be exact in binary
(eighths and quarters) so equality can be asserted where the maths is exact.
"""

from __future__ import annotations

import math

import pytest

from vectra3d import config
from vectra3d.gestures.hand_to_vector import (
    create_components,
    head_index,
    is_long_enough,
    deflection,
    resize_components,
    screen_axes,
    steer_components,
    steer_speed,
    stretch,
)

SENSITIVITY = 25
# The camera looking along +y with z up: the screen's right is +x, up is +z.
FRONT = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
# The same camera from behind, looking along -y: right is now -x.
BEHIND = ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0))


# --- Screen axes ---


def test_looking_along_y_right_is_x_and_up_is_z() -> None:
    assert screen_axes((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)) == FRONT


def test_from_behind_the_screens_right_is_minus_x() -> None:
    assert screen_axes((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)) == BEHIND


def test_looking_down_the_screens_up_leans_away_from_z() -> None:
    # Looking along (0, 1, -1)/sqrt 2, down at the scene, with a view-up of z.
    # right = d x up = (1, 0, 0) once normalised. The screen's up is
    # right x d = (0, 1, 1)/sqrt 2: square to the view, not the view-up z.
    # Using z itself would tip every created vector away from the student.
    r = 1 / math.sqrt(2)
    right, up = screen_axes((0.0, r, -r), (0.0, 0.0, 1.0))
    assert right == pytest.approx((1.0, 0.0, 0.0))
    assert up == pytest.approx((0.0, r, r))


def test_looking_straight_along_the_view_up_has_no_screen() -> None:
    assert screen_axes((0.0, 0.0, -1.0), (0.0, 0.0, 1.0)) is None


# --- Which hand is the head ---

START = ((0.5, 0.5), (0.625, 0.5))


def test_the_hand_that_moved_more_is_the_head() -> None:
    # Hand 0 moved 0.25 left, hand 1 moved 0.0625: hand 0 is pulling.
    assert head_index(START, ((0.25, 0.5), (0.6875, 0.5))) == 0
    # And the other way round.
    assert head_index(START, ((0.5625, 0.5), (0.875, 0.5))) == 1


def test_hands_that_moved_about_equally_put_the_head_on_the_right() -> None:
    # Both moved 0.25 apart: neither leads, and hand 1 is on the right.
    assert head_index(START, ((0.25, 0.5), (0.875, 0.5))) == 1
    # Hand 0 moved 0.25, hand 1 0.234375: 6.25% apart, inside the 10% margin.
    assert head_index(START, ((0.25, 0.5), (0.859375, 0.5))) == 1


def test_just_outside_the_margin_the_leading_hand_wins() -> None:
    # Hand 0 moved 0.25, hand 1 0.21875: 12.5% apart, outside the 10% margin.
    assert config.EQUAL_MOVEMENT_MARGIN < 0.125
    assert head_index(START, ((0.25, 0.5), (0.84375, 0.5))) == 0


def test_hands_that_have_not_moved_put_the_head_on_the_right() -> None:
    assert head_index(START, START) == 1
    # Whichever order they are listed in.
    swapped = (START[1], START[0])
    assert head_index(swapped, swapped) == 0


# --- How long ---


def test_the_stretch_formula() -> None:
    # Scale 0.25. Started 0.125 apart (0.5 hs), now 1.125 apart (4.5 hs).
    # (4.5 - 0.5) / 8 * 25 = 12.5.
    now = ((0.5, 0.5), (1.625, 0.5))
    assert stretch(START, 0.25, now, 0.25, SENSITIVITY) == 12.5


def test_one_full_stretch_is_the_sensitivity() -> None:
    # 8 hs of extra distance at scale 0.25 is 2.0 picture heights.
    now = ((0.5, 0.5), (2.625, 0.5))
    assert stretch(START, 0.25, now, 0.25, SENSITIVITY) == SENSITIVITY
    assert stretch(START, 0.25, now, 0.25, 10) == 10


def test_each_distance_is_measured_in_its_own_moments_hand_scale() -> None:
    # Leaning in doubles both the hands and the gap between them: 0.25 apart
    # at scale 0.5 is still 0.5 hs, so nothing has been stretched.
    now = ((0.5, 0.5), (0.75, 0.5))
    assert stretch(START, 0.25, now, 0.5, SENSITIVITY) == 0.0


def test_hands_closer_than_they_started_stretch_by_a_negative_amount() -> None:
    # 0.0625 apart is 0.25 hs, 0.25 closer than the start: -0.25 / 8 * 25.
    now = ((0.5, 0.5), (0.5625, 0.5))
    assert stretch(START, 0.25, now, 0.25, SENSITIVITY) == -0.78125


def test_hands_closer_than_they_started_create_nothing() -> None:
    assert create(((0.5, 0.5), (0.5625, 0.5))) == (0.0, 0.0, 0.0)


def test_a_hand_of_no_size_cannot_be_measured() -> None:
    assert stretch(START, 0.0, START, 0.25, SENSITIVITY) is None
    assert stretch(START, 0.25, START, 0.0, SENSITIVITY) is None


# --- The vector ---


def create(now, axes=FRONT):
    return create_components(START, 0.25, now, 0.25, axes, SENSITIVITY)


def test_pulling_right_makes_a_vector_along_the_screens_right() -> None:
    # Hand 1 pulls 1.0 to the right; hand 0 stays. Head at hand 1, 12.5 long.
    assert create(((0.5, 0.5), (1.625, 0.5))) == (12.5, 0.0, 0.0)


def test_pulling_left_with_the_other_hand_points_left() -> None:
    # Hand 0 pulls 1.0 to the left: it is the head, so the vector points left.
    assert create(((-0.5, 0.5), (0.625, 0.5))) == (-12.5, 0.0, 0.0)


def test_pulling_up_the_picture_points_up_the_screen() -> None:
    # Picture y grows downward, so a hand moving to a smaller y moves up.
    start = ((0.5, 0.5), (0.5, 0.375))
    now = ((0.5, 0.5), (0.5, -0.625))
    components = create_components(start, 0.25, now, 0.25, FRONT, SENSITIVITY)
    assert components == (0.0, 0.0, 12.5)


def test_right_follows_the_view_when_it_is_turned_around() -> None:
    # The same pull to the right, seen from behind, is -x in the world.
    assert create(((0.5, 0.5), (1.625, 0.5)), BEHIND) == (-12.5, 0.0, 0.0)


def test_a_diagonal_pull_keeps_its_angle() -> None:
    # Hand 1 pulls 1.0 right and 1.0 up. The line from tail to head is then
    # (1.125, -1.0) in the picture, which is (1.125, 1.0) on screen: x and z
    # in that ratio, with the stretch as its length.
    now = ((0.5, 0.5), (1.625, -0.5))
    components = create(now)
    length = stretch(START, 0.25, now, 0.25, SENSITIVITY)
    assert components[1] == 0.0
    assert components[0] / components[2] == pytest.approx(1.125)
    assert math.hypot(*components) == pytest.approx(length)


def test_hands_that_have_not_moved_apart_draw_the_zero_vector() -> None:
    assert create(START) == (0.0, 0.0, 0.0)


def test_nothing_to_measure_gives_none() -> None:
    assert create_components(START, 0.0, START, 0.25, FRONT, SENSITIVITY) is None


# --- Kept on release ---


def test_a_vector_shorter_than_the_minimum_is_not_kept() -> None:
    assert not is_long_enough((0.0, 0.0, 0.0))
    assert not is_long_enough((config.MIN_MAGNITUDE / 2, 0.0, 0.0))
    assert is_long_enough((config.MIN_MAGNITUDE, 0.0, 0.0))
    assert is_long_enough((12.5, 0.0, 0.0))


# --- Resizing ---

# (3, 0, 4) is 5 long, pointing (0.6, 0, 0.8).
ORIGINAL = (3.0, 0.0, 4.0)


def resize(now, scale=0.25, original=ORIGINAL):
    return resize_components(original, START, 0.25, now, scale, SENSITIVITY)


def test_pulling_apart_lengthens_the_vector_in_the_same_direction() -> None:
    # A 12.5 stretch: 5 + 12.5 = 17.5 long, still (0.6, 0, 0.8).
    components = resize(((0.5, 0.5), (1.625, 0.5)))
    assert components == pytest.approx((10.5, 0.0, 14.0))


def test_which_way_the_hands_move_does_not_turn_it() -> None:
    # The same stretch pulled vertically gives exactly the same vector.
    start = ((0.5, 0.5), (0.5, 0.375))
    now = ((0.5, 0.5), (0.5, -0.625))
    components = resize_components(ORIGINAL, start, 0.25, now, 0.25, SENSITIVITY)
    assert components == pytest.approx((10.5, 0.0, 14.0))


def test_closing_the_hands_shortens_it() -> None:
    # 0.25 hs closer: 5 - 0.78125 = 4.21875 long.
    components = resize(((0.5, 0.5), (0.5625, 0.5)))
    assert math.hypot(*components) == pytest.approx(4.21875)
    assert components[0] / components[2] == pytest.approx(0.75)


def test_it_never_shrinks_below_the_minimum() -> None:
    # A 1-long vector and hands closing by a full stretch: 1 - 25 would be
    # far below zero; it stops at the minimum, still pointing the same way.
    start = ((0.0, 0.5), (2.125, 0.5))
    now = ((0.0, 0.5), (0.125, 0.5))
    components = resize_components(
        (0.0, 1.0, 0.0), start, 0.25, now, 0.25, SENSITIVITY
    )
    assert components == (0.0, config.MIN_MAGNITUDE, 0.0)


def test_leaning_in_does_not_resize() -> None:
    # Hands and gap both doubled: still 0.5 hs apart, so the same 5.
    components = resize(((0.5, 0.5), (0.75, 0.5)), scale=0.5)
    assert components == pytest.approx(ORIGINAL)


def test_the_zero_vector_cannot_be_resized() -> None:
    assert resize(((0.5, 0.5), (1.625, 0.5)), original=(0.0, 0.0, 0.0)) is None


def test_a_resize_with_nothing_to_measure_gives_none() -> None:
    assert resize(START, scale=0.0) is None


# --- Steering (6.4) ---
#
# The camera looks along +y (FRONT), so the viewer is at -y: a vector pointing
# at the student is (0, -5, 0). Full deflection turns at 90 degrees a second,
# so half a second of it is exactly 45 degrees. 5 * cos 45 = 5 * sin 45 = H.

H = 5 * math.sqrt(0.5)
FULL = config.STEER_MAX_SPEED_HS


def turn(current, push, seconds=0.5, axes=FRONT):
    return steer_components(current, 5.0, push, seconds, axes)


def test_deflection_is_measured_from_the_anchor_in_hs_with_up_positive() -> None:
    # 0.25 right and 0.125 up the picture (smaller y) at scale 0.25.
    assert deflection((0.5, 0.5), (0.75, 0.375), 0.25) == (1.0, 0.5)
    assert deflection((0.5, 0.5), (0.75, 0.375), 0.0) is None


def test_nothing_moves_inside_the_dead_zone() -> None:
    assert steer_speed(0.0) == 0.0
    assert steer_speed(config.STEER_DEAD_ZONE_HS) == 0.0
    assert turn((0.0, -5.0, 0.0), (config.STEER_DEAD_ZONE_HS, 0.0)) == (0.0, -5.0, 0.0)


def test_speed_rises_in_a_straight_line_to_the_maximum_and_stays() -> None:
    # Halfway between 0.3 and 1.5 hs is 0.9 hs: half of 90 degrees a second.
    halfway = (config.STEER_DEAD_ZONE_HS + FULL) / 2
    assert steer_speed(halfway) == pytest.approx(config.STEER_MAX_SPEED_DEG_PER_S / 2)
    assert steer_speed(FULL) == config.STEER_MAX_SPEED_DEG_PER_S
    assert steer_speed(3 * FULL) == config.STEER_MAX_SPEED_DEG_PER_S


def test_pushing_right_swings_a_vector_pointing_at_you_to_the_right() -> None:
    # Turned 45 degrees about +z: (5 sin 45, -5 cos 45, 0). +x is screen right.
    assert turn((0.0, -5.0, 0.0), (FULL, 0.0)) == pytest.approx((H, -H, 0.0))


def test_pushing_up_tilts_a_vector_pointing_at_you_upwards() -> None:
    assert turn((0.0, -5.0, 0.0), (0.0, FULL)) == pytest.approx((0.0, -H, H))


def test_a_vector_pointing_into_the_screen_swings_the_other_way() -> None:
    # Globe-style: the far side moves against the hand.
    assert turn((0.0, 5.0, 0.0), (FULL, 0.0)) == pytest.approx((-H, H, 0.0))


def test_pushing_right_tips_a_flat_vector_pointing_right_into_the_screen() -> None:
    # This is how steering adds depth to a vector created flat on the screen.
    assert turn((5.0, 0.0, 0.0), (FULL, 0.0)) == pytest.approx((H, H, 0.0))


def test_the_same_push_turns_the_other_way_in_the_world_seen_from_behind() -> None:
    # From behind, the student's right is -x: the vector at them, (0, 5, 0),
    # swings to -x - which is still their right.
    assert turn((0.0, 5.0, 0.0), (FULL, 0.0), axes=BEHIND) == pytest.approx(
        (-H, H, 0.0)
    )


def test_a_diagonal_push_turns_once_by_its_full_amount() -> None:
    # Right and up equally, at full speed: one 45 degree turn, not two.
    push = (FULL, FULL)
    turned = turn((0.0, -5.0, 0.0), push)
    cosine = -turned[1] / 5.0
    assert math.degrees(math.acos(cosine)) == pytest.approx(45.0)
    assert turned[0] == pytest.approx(turned[2])


def test_the_turn_follows_the_time_step() -> None:
    # A tenth of a second at full speed: 9 degrees.
    turned = turn((0.0, -5.0, 0.0), (FULL, 0.0), seconds=0.1)
    assert math.degrees(math.atan2(turned[0], -turned[1])) == pytest.approx(9.0)
    assert turn((0.0, -5.0, 0.0), (FULL, 0.0), seconds=0.0) == (0.0, -5.0, 0.0)


def test_the_magnitude_does_not_creep_over_many_frames() -> None:
    vector = (3.0, -4.0, 0.0)
    for step in range(1000):
        push = (FULL * math.cos(step), FULL * math.sin(step))
        vector = steer_components(vector, 5.0, push, 0.033, FRONT)
    assert math.hypot(*vector) == pytest.approx(5.0, abs=1e-12)

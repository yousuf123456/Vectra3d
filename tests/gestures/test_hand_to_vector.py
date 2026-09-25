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
    screen_axes,
    stretch_magnitude,
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
    assert stretch_magnitude(START, 0.25, now, 0.25, SENSITIVITY) == 12.5


def test_one_full_stretch_is_the_sensitivity() -> None:
    # 8 hs of extra distance at scale 0.25 is 2.0 picture heights.
    now = ((0.5, 0.5), (2.625, 0.5))
    assert stretch_magnitude(START, 0.25, now, 0.25, SENSITIVITY) == SENSITIVITY
    assert stretch_magnitude(START, 0.25, now, 0.25, 10) == 10


def test_each_distance_is_measured_in_its_own_moments_hand_scale() -> None:
    # Leaning in doubles both the hands and the gap between them: 0.25 apart
    # at scale 0.5 is still 0.5 hs, so nothing has been stretched.
    now = ((0.5, 0.5), (0.75, 0.5))
    assert stretch_magnitude(START, 0.25, now, 0.5, SENSITIVITY) == 0.0


def test_hands_closer_than_they_started_give_nothing() -> None:
    now = ((0.5, 0.5), (0.5625, 0.5))
    assert stretch_magnitude(START, 0.25, now, 0.25, SENSITIVITY) == 0.0


def test_a_hand_of_no_size_cannot_be_measured() -> None:
    assert stretch_magnitude(START, 0.0, START, 0.25, SENSITIVITY) is None
    assert stretch_magnitude(START, 0.25, START, 0.0, SENSITIVITY) is None


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
    length = stretch_magnitude(START, 0.25, now, 0.25, SENSITIVITY)
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

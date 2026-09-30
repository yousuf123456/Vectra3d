"""Hand positions into vectors (`interaction-spec.md` sections 6.1 to 6.5).

Every expected value is worked out by hand. Points are in picture-height
units, as the metrics give them; distances are chosen to be exact in binary
(eighths and quarters) so equality can be asserted where the maths is exact.
"""

from __future__ import annotations

import math

import pytest

from vectra3d import config
from vectra3d.gestures.hand_to_vector import (
    Heading,
    Snap,
    at_pole,
    create_components,
    drag_meridian,
    hand_movement,
    head_index,
    heading_components,
    heading_of,
    is_long_enough,
    leave_pole,
    meridian_of,
    resize_components,
    screen_axes,
    snap_near,
    snapped,
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


# --- Steering: grab and drag (6.4) ---
#
# The angles change by the steering rate for every hs the hand moves.
# Movements are written as `turn(degrees)`, the hs that turn that far, so
# the expected angles stay hand-calculated whatever the rate is tuned to.

RATE = config.STEER_DEG_PER_HS
# Pointing at a student who looks along +y: (0, -5, 0).
AT_YOU = Heading(90.0, 270.0)


def turn(degrees: float) -> float:
    """The hand movement, in hs, that turns a vector this many degrees."""
    return degrees / RATE


def drag(heading: Heading, movement: tuple[float, float]) -> Heading:
    """A heading dragged by `movement`, starting on its own side of z."""
    return drag_meridian(meridian_of(heading), movement).heading


def test_hand_movement_is_in_hs_with_up_positive() -> None:
    # 0.25 right and 0.125 up the picture (smaller y) at scale 0.25.
    assert hand_movement((0.5, 0.5), (0.75, 0.375), 0.25) == (1.0, 0.5)
    assert hand_movement((0.5, 0.5), (0.75, 0.375), 0.0) is None


def test_a_still_hand_leaves_the_vector_still() -> None:
    assert hand_movement((0.5, 0.5), (0.5, 0.5), 0.25) == (0.0, 0.0)
    assert drag(AT_YOU, (0.0, 0.0)) == AT_YOU


def test_dragging_up_raises_the_head_towards_z() -> None:
    raised = drag(AT_YOU, (0.0, turn(45.0)))
    assert (raised.theta, raised.phi) == pytest.approx((45.0, 270.0))


def test_dragging_down_lowers_the_head_towards_minus_z() -> None:
    lowered = drag(AT_YOU, (0.0, -turn(45.0)))
    assert (lowered.theta, lowered.phi) == pytest.approx((135.0, 270.0))


def test_the_turn_is_the_movement_times_the_rate() -> None:
    # Half an hs up at 90 degrees per hs is 45 degrees; a tenth is 9.
    assert drag(AT_YOU, (0.0, 0.5)).theta == pytest.approx(90.0 - 0.5 * RATE)
    assert drag(AT_YOU, (0.0, 0.1)).theta == pytest.approx(90.0 - 0.1 * RATE)


@pytest.mark.parametrize("phi", [0.0, 90.0, 180.0, 270.0, 123.0])
def test_up_raises_the_head_wherever_it_points(phi: float) -> None:
    # The fault angle steering replaced: under globe-style steering, a vector
    # pointing away from the viewer rose when the hand went down.
    after = heading_components(drag(Heading(90.0, phi), (0.0, turn(45.0))), 5.0)
    # theta 45: z = 5 cos 45.
    assert after[2] == pytest.approx(5 * math.sqrt(0.5))


def test_dragging_up_carries_on_over_the_top() -> None:
    # The user's report: at the top the vector stopped, and the hand had to
    # go back down before it moved again. Now 50 up from theta 20 goes 20 to
    # the top and 30 down the far side: theta 30 at phi 30 + 180.
    over = drag_meridian(meridian_of(Heading(20.0, 30.0)), (0.0, turn(50.0)))
    assert (over.heading.theta, over.heading.phi) == pytest.approx((30.0, 210.0))
    # And 10 back down retraces the way it came.
    back = drag_meridian(over, (0.0, -turn(10.0))).heading
    assert (back.theta, back.phi) == pytest.approx((20.0, 210.0))


def test_dragging_down_carries_on_under_the_bottom() -> None:
    under = drag_meridian(meridian_of(Heading(160.0, 30.0)), (0.0, -turn(50.0)))
    assert (under.heading.theta, under.heading.phi) == pytest.approx((150.0, 210.0))


@pytest.mark.parametrize("upward", [1.0, -1.0])
def test_a_full_vertical_turn_comes_all_the_way_round(upward: float) -> None:
    # 360 one-degree drags up (or down) from pointing at the student: every
    # step turns the head exactly one degree, through both poles, and it
    # ends where it began.
    meridian = meridian_of(AT_YOU)
    head = heading_components(meridian.heading, 1.0)
    for _ in range(360):
        meridian = drag_meridian(meridian, (0.0, upward * turn(1.0)))
        after = heading_components(meridian.heading, 1.0)
        step = math.degrees(math.acos(min(1.0, sum(a * b for a, b in zip(head, after)))))
        assert step == pytest.approx(1.0, abs=1e-6)
        head = after
    assert head == pytest.approx(heading_components(AT_YOU, 1.0), abs=1e-9)


def test_right_always_raises_phi_and_left_lowers_it() -> None:
    assert drag(Heading(90.0, 0.0), (turn(45.0), 0.0)).phi == pytest.approx(45.0)
    assert drag(Heading(90.0, 0.0), (-turn(45.0), 0.0)).phi == pytest.approx(315.0)


@pytest.mark.parametrize("phi", [0.0, 90.0, 180.0, 270.0, 123.0])
@pytest.mark.parametrize("theta", [10.0, 90.0, 170.0])
def test_right_turns_the_same_way_round_wherever_the_vector_points(
    theta: float, phi: float
) -> None:
    # The user's request: the way a hand movement turns the vector is fixed,
    # not chosen from where the vector points.
    assert drag(Heading(theta, phi), (turn(10.0), 0.0)).phi == pytest.approx(
        (phi + 10.0) % 360.0
    )


def test_over_the_top_right_still_turns_the_same_way_round() -> None:
    # Gone over the top, the head is at phi + 180, and right still raises it.
    over = drag_meridian(meridian_of(Heading(20.0, 30.0)), (0.0, turn(50.0)))
    turned = drag_meridian(over, (turn(10.0), 0.0))
    assert turned.heading.phi == pytest.approx(over.heading.phi + 10.0)


def test_phi_keeps_going_round_past_360() -> None:
    assert drag(Heading(90.0, 350.0), (turn(45.0), 0.0)).phi == pytest.approx(35.0)


def test_a_full_turn_of_small_drags_comes_all_the_way_round() -> None:
    # What the joystick with sticky snaps could not do: 360 one-degree
    # drags pass every axis and plane and end where they began.
    heading = Heading(90.0, 10.0)
    phis = []
    for _ in range(360):
        heading = drag(heading, (turn(1.0), 0.0))
        phis.append(heading.phi)
    assert heading.theta == 90.0
    assert heading.phi == pytest.approx(10.0)
    # Every step was one degree: nothing stuck on the way round.
    steps = [(b - a) % 360.0 for a, b in zip([10.0] + phis, phis)]
    assert steps == pytest.approx([1.0] * 360)


def test_a_diagonal_changes_each_angle_by_its_own_part() -> None:
    turned = drag(Heading(90.0, 0.0), (turn(20.0), turn(30.0)))
    assert turned.theta == pytest.approx(60.0)
    assert turned.phi == pytest.approx(20.0)


def test_the_magnitude_does_not_creep_over_many_frames() -> None:
    heading = Heading(60.0, 10.0)
    for step in range(1000):
        movement = (0.05 * math.cos(step), 0.05 * math.sin(step))
        heading = drag(heading, movement)
        vector = heading_components(heading, 5.0)
        assert math.hypot(*vector) == pytest.approx(5.0, abs=1e-12)


def test_a_vector_has_its_angles_and_the_zero_vector_none() -> None:
    assert heading_of((0.0, -5.0, 0.0)) == AT_YOU
    assert heading_of((0.0, 0.0, 2.0)) == Heading(0.0, 0.0)
    assert heading_of((0.0, 0.0, 0.0)) is None


# --- Snapping on release (6.5) ---
#
# Theta snaps to 0, 90 or 180 and phi to 0, 90, 180 or 270, each within
# 5 degrees. `snap_near` says what a release here would land on.


def test_theta_snaps_into_the_floor_within_5_degrees_and_not_beyond() -> None:
    assert snap_near(Heading(94.9, 45.0)) == Snap(90.0, None)
    assert snap_near(Heading(85.1, 45.0)) == Snap(90.0, None)
    assert snap_near(Heading(95.1, 45.0)) is None


def test_phi_snaps_into_the_upright_planes() -> None:
    assert snap_near(Heading(60.0, 4.9)) == Snap(None, 0.0)
    assert snap_near(Heading(60.0, 94.0)) == Snap(None, 90.0)
    assert snap_near(Heading(60.0, 184.0)) == Snap(None, 180.0)
    assert snap_near(Heading(60.0, 5.1)) is None


def test_phi_snaps_across_360() -> None:
    assert snap_near(Heading(60.0, 356.0)) == Snap(None, 0.0)


def test_both_angles_snapped_is_an_axis() -> None:
    assert snap_near(Heading(93.0, 184.0)) == Snap(90.0, 180.0)


def test_on_the_z_axis_phi_does_not_snap() -> None:
    assert snap_near(Heading(4.0, 30.0)) == Snap(0.0, None)
    assert snap_near(Heading(4.0, 0.0)) == Snap(0.0, None)
    assert snap_near(Heading(177.0, 90.0)) == Snap(180.0, None)


def test_a_vector_exactly_on_an_axis_or_plane_is_in_reach_of_it() -> None:
    # So a release there snaps to where it already is, which changes nothing.
    assert snap_near(heading_of((0.0, 0.0, 5.0))) == Snap(0.0, None)
    assert snap_near(heading_of((0.0, -5.0, 0.0))) == Snap(90.0, 270.0)
    assert snap_near(heading_of((3.0, 0.0, 4.0))) == Snap(None, 0.0)
    assert snap_near(heading_of((3.0, 4.0, 0.0))) == Snap(90.0, None)
    assert snap_near(heading_of((1.0, 2.0, 3.0))) is None


def test_snaps_are_named_for_the_camera_strip() -> None:
    assert Snap(0.0, None).label == "+z axis"
    assert Snap(180.0, None).label == "-z axis"
    assert Snap(90.0, 0.0).label == "+x axis"
    assert Snap(90.0, 90.0).label == "+y axis"
    assert Snap(90.0, 180.0).label == "-x axis"
    assert Snap(90.0, 270.0).label == "-y axis"
    assert Snap(90.0, None).label == "XY plane"
    assert Snap(None, 0.0).label == "XZ plane"
    assert Snap(None, 180.0).label == "XZ plane"
    assert Snap(None, 90.0).label == "YZ plane"
    assert Snap(None, 270.0).label == "YZ plane"


def test_the_landed_heading_takes_each_snapped_angle() -> None:
    assert snapped(Heading(93.0, 37.0), Snap(90.0, None)) == Heading(90.0, 37.0)
    assert snapped(Heading(93.0, 3.0), Snap(90.0, 0.0)) == Heading(90.0, 0.0)
    assert snapped(Heading(93.0, 37.0), None) == Heading(93.0, 37.0)


def test_a_vector_on_an_axis_or_plane_is_exactly_there() -> None:
    # cos 90 degrees is 6e-17 in floating point; it is set to zero.
    flat = heading_components(Heading(90.0, 37.0), 5.0)
    assert flat[2] == 0.0
    assert math.hypot(*flat) == pytest.approx(5.0)
    assert heading_components(Heading(90.0, 180.0), 5.0) == (-5.0, 0.0, 0.0)
    assert heading_components(Heading(90.0, 90.0), 5.0) == (0.0, 5.0, 0.0)
    assert heading_components(Heading(180.0, 0.0), 5.0) == (0.0, 0.0, -5.0)
    upright = heading_components(Heading(50.0, 270.0), 5.0)
    assert upright[0] == 0.0
    assert upright[1] < 0.0


# --- Leaving the z axis (6.4) ---
#
# Seen along +y (FRONT) the screen's up is z, which has no floor shadow, so up
# and down on screen go away from and towards the student: +y and -y.


def test_at_the_top_right_tips_the_head_right() -> None:
    left = leave_pole(Heading(0.0, 0.0), (turn(45.0), 0.0), FRONT)
    assert left.theta == pytest.approx(45.0)
    assert left.phi == pytest.approx(0.0, abs=1e-9)


def test_at_the_top_down_tips_the_head_towards_the_student() -> None:
    left = leave_pole(Heading(0.0, 0.0), (0.0, -turn(45.0)), FRONT)
    assert left.theta == pytest.approx(45.0)
    assert left.phi == pytest.approx(270.0)


def test_at_the_top_up_does_nothing() -> None:
    assert leave_pole(Heading(0.0, 0.0), (0.0, turn(45.0)), FRONT) == Heading(0.0, 0.0)


def test_at_the_bottom_up_tips_the_head_away_and_down_does_nothing() -> None:
    left = leave_pole(Heading(180.0, 0.0), (0.0, turn(45.0)), FRONT)
    assert left.theta == pytest.approx(135.0)
    assert left.phi == pytest.approx(90.0)
    assert leave_pole(Heading(180.0, 0.0), (0.0, -turn(45.0)), FRONT) == Heading(
        180.0, 0.0
    )


def test_a_diagonal_keeps_only_the_part_that_leaves_the_axis() -> None:
    # 30 up and 20 right at the top: the up part is dropped, 20 right stays.
    left = leave_pole(Heading(0.0, 0.0), (turn(20.0), turn(30.0)), FRONT)
    assert left.theta == pytest.approx(20.0)
    assert left.phi == pytest.approx(0.0, abs=1e-9)


def test_a_still_hand_at_the_axis_leaves_it_there() -> None:
    assert leave_pole(Heading(0.0, 0.0), (0.0, 0.0), FRONT) == Heading(0.0, 0.0)


def test_in_a_raised_view_right_still_moves_the_head_right_on_screen() -> None:
    raised = screen_axes((-4.0, 3.0, -2.5), (0.0, 0.0, 1.0))
    right, screen_up = raised
    # How far the head moved from straight up, along the screen's right for
    # a drag right, and along its up for a drag down (expected negative).
    for movement, along, sign in (
        ((turn(9.0), 0.0), right, 1),
        ((0.0, -turn(9.0)), screen_up, -1),
    ):
        head = heading_components(leave_pole(Heading(0.0, 0.0), movement, raised), 1.0)
        moved = sum((h - s) * a for h, s, a in zip(head, (0.0, 0.0, 1.0), along))
        # 9 degrees: 0.16 across; about 0.08 down, since the view looks down.
        assert sign * moved > 0.05


def test_the_z_axis_is_a_pole_and_nothing_else_is() -> None:
    assert at_pole(Heading(0.0, 30.0))
    assert at_pole(Heading(180.0, 0.0))
    assert not at_pole(Heading(0.5, 0.0))

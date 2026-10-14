"""The direction angle arcs on the active vector (`interaction-spec.md` 2.4, 10).

alpha from +x, beta from +y, gamma from +z, each an arc round to the vector.
Geometry only, worked out by hand, without a plotter.
"""

from __future__ import annotations

import math

import pytest

from vectra3d.render.overlays import (
    ARC_POINTS,
    angle_text,
    arc_tag_position,
    direction_arc,
)

R = 2.0
X, Y, Z = 0, 1, 2
H = R * math.sqrt(0.5)


def on_circle(arc) -> bool:
    return all(math.hypot(*point) == pytest.approx(R) for point in arc)


def test_alpha_runs_from_the_x_axis_to_the_vector() -> None:
    # (1, 0, 1): alpha 45 degrees, in the XZ plane.
    arc = direction_arc((1.0, 0.0, 1.0), X, R)
    assert len(arc) == ARC_POINTS
    assert arc[0] == pytest.approx((R, 0.0, 0.0))
    assert arc[-1] == pytest.approx((H, 0.0, H))
    assert on_circle(arc)


def test_beta_and_gamma_start_on_their_own_axes() -> None:
    # (0, 1, 1): beta 45 from +y, gamma 45 from +z; both end on the vector.
    beta = direction_arc((0.0, 1.0, 1.0), Y, R)
    gamma = direction_arc((0.0, 1.0, 1.0), Z, R)
    assert beta[0] == pytest.approx((0.0, R, 0.0))
    assert gamma[0] == pytest.approx((0.0, 0.0, R))
    assert beta[-1] == pytest.approx((0.0, H, H))
    assert gamma[-1] == pytest.approx((0.0, H, H))
    assert on_circle(beta) and on_circle(gamma)


def test_an_obtuse_angle_sweeps_past_the_right_angle() -> None:
    # (-1, 0, 1): alpha 135 degrees, so the arc goes over +z on its way.
    arc = direction_arc((-1.0, 0.0, 1.0), X, R)
    assert max(point[2] for point in arc) == pytest.approx(R, abs=0.01)
    assert arc[-1] == pytest.approx((-H, 0.0, H))


def test_a_square_angle_is_a_quarter_turn() -> None:
    # (0, 0, 3) is 90 degrees from +x: the arc runs from +x up to +z.
    arc = direction_arc((0.0, 0.0, 3.0), X, R)
    assert arc[0] == pytest.approx((R, 0.0, 0.0))
    assert arc[-1] == pytest.approx((0.0, 0.0, R))


@pytest.mark.parametrize("axis", [X, Y, Z])
def test_no_arc_along_the_axis_itself(axis: int) -> None:
    components = [0.0, 0.0, 0.0]
    components[axis] = 4.0
    assert direction_arc(tuple(components), axis, R) == ()


@pytest.mark.parametrize(
    ("axis", "through"),
    [(X, (0.0, H, H)), (Y, (H, 0.0, H)), (Z, (H, H, 0.0))],
)
def test_opposite_an_axis_the_half_turn_goes_through_the_diagonal(
    axis: int, through
) -> None:
    # The plane holding an axis and a vector pointing straight back along it
    # is not defined. The arc turns through the diagonal between the other
    # two axes: through either axis it would lie on top of that axis's own
    # quarter-turn arc to the same vector.
    components = [0.0, 0.0, 0.0]
    components[axis] = -3.0
    arc = direction_arc(tuple(components), axis, R)
    start = [0.0, 0.0, 0.0]
    start[axis] = R
    assert arc[0] == pytest.approx(tuple(start))
    assert arc[len(arc) // 2] == pytest.approx(through, abs=0.05)
    assert arc[-1] == pytest.approx(tuple(-v for v in start))


def test_the_zero_vector_has_no_arcs() -> None:
    assert all(direction_arc((0.0, 0.0, 0.0), axis, R) == () for axis in (X, Y, Z))


def test_the_values_are_one_line_like_the_info_panel() -> None:
    # (1, 0, 1): alpha 45, beta 90, gamma 45. One caption beside the head,
    # not a box at each arc (G5.6).
    assert angle_text((1.0, 0.0, 1.0)) == "α 45.00°   β 90.00°   γ 45.00°"
    assert angle_text((0.0, 0.0, -2.0)) == "α 90.00°   β 90.00°   γ 180.00°"
    assert angle_text((0.0, 0.0, 0.0)) is None


def test_each_arc_is_tagged_just_outside_its_middle() -> None:
    # alpha for (1, 0, 1) at radius 2 runs from +x to 45 degrees; its middle
    # is about 22.5 degrees up from x, and the letter sits 1.2 times further out.
    arc = direction_arc((1.0, 0.0, 1.0), X, R)
    t = math.radians(45.0 * (ARC_POINTS // 2) / (ARC_POINTS - 1))
    assert arc_tag_position(arc) == pytest.approx(
        (1.2 * R * math.cos(t), 0.0, 1.2 * R * math.sin(t))
    )
    assert arc_tag_position(()) is None

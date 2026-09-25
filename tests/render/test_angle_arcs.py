"""The theta and phi arcs shown while steering (`interaction-spec.md` 2.3, 10).

Geometry only, worked out by hand, without a plotter.
"""

from __future__ import annotations

import math

import pytest

from vectra3d.render.overlays import (
    ARC_POINTS,
    angle_labels,
    angle_text,
    arc_tag_position,
    phi_arc,
    theta_arc,
)

R = 2.0


def test_theta_runs_from_the_z_axis_to_the_vector() -> None:
    # (1, 0, 1): theta 45 degrees, leaning towards +x.
    arc = theta_arc((1.0, 0.0, 1.0), R)
    assert len(arc) == ARC_POINTS
    assert arc[0] == pytest.approx((0.0, 0.0, R))
    h = R * math.sqrt(0.5)
    assert arc[-1] == pytest.approx((h, 0.0, h))
    # Every point is on the circle of radius R.
    assert all(math.hypot(*point) == pytest.approx(R) for point in arc)


def test_theta_leans_towards_the_vectors_own_side() -> None:
    # (0, -1, 0): theta 90 degrees, the arc ends on the -y axis.
    assert theta_arc((0.0, -1.0, 0.0), R)[-1] == pytest.approx((0.0, -R, 0.0))


def test_no_theta_arc_along_plus_z() -> None:
    assert theta_arc((0.0, 0.0, 3.0), R) == ()


def test_along_minus_z_the_theta_arc_is_a_half_turn_through_x() -> None:
    arc = theta_arc((0.0, 0.0, -3.0), R)
    assert arc[0] == pytest.approx((0.0, 0.0, R))
    assert arc[len(arc) // 2] == pytest.approx((R, 0.0, 0.0), abs=0.05)
    assert arc[-1] == pytest.approx((0.0, 0.0, -R))


def test_phi_turns_counterclockwise_from_x() -> None:
    # (0, 1, 5): phi 90 degrees - a quarter turn from +x to +y, flat.
    arc = phi_arc((0.0, 1.0, 5.0), R)
    assert arc[0] == pytest.approx((R, 0.0, 0.0))
    assert arc[-1] == pytest.approx((0.0, R, 0.0), abs=1e-12)
    assert all(point[2] == 0.0 for point in arc)


def test_phi_past_180_goes_the_long_way_round() -> None:
    # (0, -1, 0): phi 270 degrees, so the arc passes through +y and -x on the
    # way - the short way round, clockwise, would touch neither.
    arc = phi_arc((0.0, -1.0, 0.0), R)
    assert max(point[1] for point in arc) == pytest.approx(R, abs=0.01)
    assert min(point[0] for point in arc) == pytest.approx(-R, abs=0.01)
    assert arc[-1] == pytest.approx((0.0, -R, 0.0), abs=1e-12)


def test_no_phi_arc_along_the_z_axis() -> None:
    assert phi_arc((0.0, 0.0, 3.0), R) == ()
    assert phi_arc((0.0, 0.0, -3.0), R) == ()


def test_the_labels_read_like_the_info_panel() -> None:
    assert angle_labels((1.0, 0.0, 1.0)) == ("θ 45.00°", "φ 0.00°")
    assert angle_labels((0.0, -1.0, 0.0)) == ("θ 90.00°", "φ 270.00°")


def test_phi_has_no_label_along_the_z_axis() -> None:
    assert angle_labels((0.0, 0.0, 2.0)) == ("θ 0.00°", None)


def test_the_zero_vector_has_no_angles() -> None:
    assert angle_labels((0.0, 0.0, 0.0)) == (None, None)
    assert theta_arc((0.0, 0.0, 0.0), R) == ()


def test_the_values_are_one_line_beside_the_head() -> None:
    # One caption under the letter, not a box at each arc (G5.6).
    assert angle_text((1.0, 0.0, 1.0)) == "θ 45.00°   φ 0.00°"
    assert angle_text((0.0, 0.0, 2.0)) == "θ 0.00°"
    assert angle_text((0.0, 0.0, 0.0)) is None


def test_each_arc_is_tagged_just_outside_its_middle() -> None:
    # theta for (1, 0, 1) at radius 2 runs from +z to 45 degrees; its middle
    # is 22.5 degrees down from z, and the letter sits 1.2 times further out.
    arc = theta_arc((1.0, 0.0, 1.0), R)
    t = math.radians(45.0 * (ARC_POINTS // 2) / (ARC_POINTS - 1))
    assert arc_tag_position(arc) == pytest.approx(
        (1.2 * R * math.sin(t), 0.0, 1.2 * R * math.cos(t))
    )
    assert arc_tag_position(()) is None

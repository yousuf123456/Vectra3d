"""Where the axis numbers sit for a given viewpoint.

The numbers used to be pushed off their axis in a fixed world direction,
which suits one viewpoint and no other: turn the scene and they land on the
axis, across a vector, or on top of each other, and looking straight down an
axis puts every one of its numbers on the origin at once.

These tests pin the rules that replaced that. Whether the result reads well
is still a matter for the eye; what is checked here is that the direction is
always usable and that a head-on axis is refused.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from vectra3d.render.scene import label_offset_direction

X = np.array([1.0, 0.0, 0.0])
Y = np.array([0.0, 1.0, 0.0])
Z = np.array([0.0, 0.0, 1.0])
UP = np.array([0.0, 0.0, 1.0])


def looking_along(direction: np.ndarray) -> np.ndarray:
    return np.array(direction, dtype=float)


class TestAnAxisPointingAtTheCamera:
    @pytest.mark.parametrize("axis", [X, Y, Z])
    def test_is_refused_head_on(self, axis: np.ndarray) -> None:
        # Its numbers would all project onto the origin.
        assert label_offset_direction(axis, looking_along(axis), UP) is None

    @pytest.mark.parametrize("axis", [X, Y, Z])
    def test_is_refused_from_directly_behind_too(self, axis: np.ndarray) -> None:
        # Looking up the axis from the far side is just as unreadable.
        assert label_offset_direction(axis, looking_along(-axis), UP) is None

    def test_is_allowed_once_clearly_off_axis(self) -> None:
        # 30 degrees away from the viewing direction is plenty.
        view = np.array([math.cos(math.radians(30)), math.sin(math.radians(30)), 0.0])
        assert label_offset_direction(X, view, UP) is not None


class TestTheDirectionItReturns:
    @pytest.mark.parametrize(
        ("axis", "view"),
        [
            (X, Y),
            (Y, X),
            (Z, X),
            (X, np.array([0.3, -0.9, 0.3])),
            (Z, np.array([1.0, -1.35, 0.75])),
        ],
    )
    def test_is_a_unit_vector(self, axis: np.ndarray, view: np.ndarray) -> None:
        # It is multiplied by the offset distance, so a direction of any other
        # length would move the numbers the wrong distance from the axis.
        offset = label_offset_direction(axis, view, UP)
        assert offset is not None
        assert float(np.linalg.norm(offset)) == pytest.approx(1.0)

    @pytest.mark.parametrize(
        ("axis", "view"),
        [(X, Y), (Y, X), (Z, X), (X, np.array([0.3, -0.9, 0.3]))],
    )
    def test_is_square_to_its_own_axis(
        self, axis: np.ndarray, view: np.ndarray
    ) -> None:
        # Any component along the axis would slide the number towards the
        # next one rather than away from the line.
        offset = label_offset_direction(axis, view, UP)
        assert offset is not None
        assert float(np.dot(offset, axis)) == pytest.approx(0.0)

    @pytest.mark.parametrize(
        ("axis", "view"),
        [(X, Y), (Y, X), (Z, X), (X, np.array([0.3, -0.9, 0.3]))],
    )
    def test_lies_in_the_plane_of_the_screen(
        self, axis: np.ndarray, view: np.ndarray
    ) -> None:
        # A direction with any depth in it would push the number towards or
        # away from the camera, changing nothing about where it is read.
        offset = label_offset_direction(axis, view, UP)
        assert offset is not None
        unit_view = view / np.linalg.norm(view)
        assert float(np.dot(offset, unit_view)) == pytest.approx(0.0)


class TestWhichWayItPushes:
    def test_a_horizontal_axis_sends_its_numbers_downwards(self) -> None:
        # The x axis seen from along y runs across the screen, so its numbers
        # hang below it, as on a printed graph.
        offset = label_offset_direction(X, -Y, UP)
        assert offset is not None
        assert float(np.dot(offset, UP)) < 0.0

    def test_an_upright_axis_sends_its_numbers_sideways(self) -> None:
        # The z axis runs up the screen, where "below" is meaningless. The
        # numbers go to the left instead of onto the line.
        view = -Y
        offset = label_offset_direction(Z, view, UP)
        assert offset is not None
        assert float(np.dot(offset, UP)) == pytest.approx(0.0, abs=1e-9)
        right = np.cross(view / np.linalg.norm(view), UP)
        assert float(np.dot(offset, right)) < 0.0

    def test_the_numbers_stay_below_the_axis_from_either_side(self) -> None:
        # This is the whole point. The old fixed nudge sent the x numbers
        # towards -y always, which reads correctly from the front and puts
        # them on the wrong side of the axis from behind. Chasing the screen
        # instead means they hang below the line from both.
        for view in (-Y, Y):
            offset = label_offset_direction(X, view, UP)
            assert offset is not None
            assert float(np.dot(offset, UP)) < 0.0

    def test_the_direction_changes_as_the_view_changes(self) -> None:
        # Tilting over the scene and ducking under it are different views, so
        # "sideways from the x axis, on screen" is a different world
        # direction in each. A fixed nudge cannot be right for both, which is
        # what was wrong before; both of these still read below the axis.
        from_above = label_offset_direction(X, np.array([0.0, -1.0, -1.0]), UP)
        from_below = label_offset_direction(X, np.array([0.0, -1.0, 1.0]), UP)
        assert from_above is not None and from_below is not None
        assert not np.allclose(from_above, from_below)
        assert float(np.dot(from_above, UP)) < 0.0
        assert float(np.dot(from_below, UP)) < 0.0

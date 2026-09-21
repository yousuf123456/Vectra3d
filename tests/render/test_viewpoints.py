"""The named viewpoints behind the toolbar's view buttons.

Only the directions are tested. Whether a view reads clearly on screen is a
matter for the eye, as with the rest of the scene.
"""

from __future__ import annotations

import math

import pytest

from vectra3d.render.scene import VIEWPOINTS
from vectra3d.ui.main_window import VIEW_HINTS

AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


def test_every_view_has_a_button_hint() -> None:
    # A view with no hint would be a button with no tooltip; a hint with no
    # view would be a button that does nothing.
    assert set(VIEWPOINTS) == set(VIEW_HINTS)


@pytest.mark.parametrize("name", sorted(VIEWPOINTS))
def test_each_view_looks_straight_down_one_axis(name: str) -> None:
    # Exactly one component non-zero is what makes the view square-on: any
    # other direction foreshortens two axes at once, which is the guesswork
    # these buttons exist to remove.
    direction, _ = VIEWPOINTS[name]
    assert sum(1 for value in direction if value != 0.0) == 1


@pytest.mark.parametrize("name", sorted(VIEWPOINTS))
def test_up_is_square_to_the_direction_looked_along(name: str) -> None:
    # If "up" had any part along the viewing direction the camera would be
    # tilted, and VTK would have to correct it into something unasked for.
    direction, view_up = VIEWPOINTS[name]
    dot = sum(d * u for d, u in zip(direction, view_up))
    assert dot == pytest.approx(0.0)


@pytest.mark.parametrize("name", sorted(VIEWPOINTS))
def test_directions_and_ups_are_unit_length(name: str) -> None:
    # `set_view` multiplies the direction by the camera distance, so a
    # direction that was not one unit long would change how far away the
    # camera sits and make one view zoom differently from the others.
    direction, view_up = VIEWPOINTS[name]
    assert math.hypot(*direction) == pytest.approx(1.0)
    assert math.hypot(*view_up) == pytest.approx(1.0)


def test_the_three_views_look_along_three_different_axes() -> None:
    looked_along = {
        next(axis for axis, i in AXIS_INDEX.items() if direction[i] != 0.0)
        for direction, _ in VIEWPOINTS.values()
    }
    assert looked_along == {"x", "y", "z"}


@pytest.mark.parametrize("name", ["Front", "Right"])
def test_z_is_up_in_the_side_views(name: str) -> None:
    # The student reads height as height in these two, matching every
    # textbook diagram of a z-up scene.
    _, view_up = VIEWPOINTS[name]
    assert view_up == (0.0, 0.0, 1.0)


def test_the_top_view_puts_y_up_because_z_points_at_the_viewer() -> None:
    # Looking down z, "z up" would be meaningless: it points out of the
    # screen. +y at the top makes the view read as a map of the XY plane.
    direction, view_up = VIEWPOINTS["Top"]
    assert direction == (0.0, 0.0, 1.0)
    assert view_up == (0.0, 1.0, 0.0)

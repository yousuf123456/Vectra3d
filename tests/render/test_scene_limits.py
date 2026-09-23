"""What the scene can be sized to, and what it refuses.

These cover a crash found at G3.2 and fixed in its own step: typing 1e308 into
the create form sized the world to infinity and took the window down with
`ValueError: matrix must have finite values` from deep inside VTK.

There were two faults. The extent sequence was built by multiplying a running
decade by ten, which compounds rounding error until the step meant to be 1e308
lands under its own target - so the search rejected it and took 2e308, which
overflows. And nothing bounded the input in the first place, because VTK holds
point coordinates as 32-bit floats and cannot draw beyond about 3.4e38 whatever
the sequence says.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
import pyvista as pv

from vectra3d.render.scene import (
    MAX_COMPONENT,
    MAX_EXTENT,
    MIN_EXTENT,
    extent_for,
    extent_for_vectors,
    extent_steps,
)
from vectra3d.render.vector_actor import VectorActors
from vectra3d.state.models import Vector


class TestTheExtentSequence:
    def test_it_starts_where_the_spec_says(self) -> None:
        assert list(extent_steps())[:6] == [10.0, 20.0, 50.0, 100.0, 200.0, 500.0]

    def test_every_step_is_finite(self) -> None:
        # The whole bug in one assertion: the sequence used to reach infinity.
        assert all(math.isfinite(step) for step in extent_steps())

    def test_it_ends_at_the_largest_drawable_extent(self) -> None:
        assert list(extent_steps())[-1] == MAX_EXTENT

    def test_the_steps_are_exact_powers_and_do_not_drift(self) -> None:
        # Repeated multiplication reached 1e100 as 1.0000000000000006e+100.
        # Every step must be exactly the number it is meant to be, or the
        # comparison in `extent_for` can miss the step that fits.
        wanted = {
            multiplier * 10.0**power
            for power in range(1, 39)
            for multiplier in (1, 2, 5)
        }
        steps = set(extent_steps())
        assert steps <= wanted
        assert 1e30 in steps
        assert 1e20 in steps

    def test_the_steps_only_ever_increase(self) -> None:
        steps = list(extent_steps())
        assert steps == sorted(steps)
        assert len(set(steps)) == len(steps)


class TestExtentFor:
    def test_it_never_goes_below_the_minimum(self) -> None:
        assert extent_for(0.0) == MIN_EXTENT
        assert extent_for(3.0) == MIN_EXTENT

    def test_a_value_on_the_boundary_fits(self) -> None:
        assert extent_for(10.0) == 10.0

    def test_it_fits_a_value_at_the_cap(self) -> None:
        assert math.isfinite(extent_for(MAX_COMPONENT))

    @pytest.mark.parametrize("value", [1e39, 1e100, 1e308])
    def test_a_value_too_large_to_draw_is_refused(self, value: float) -> None:
        # It used to return infinity for 1e308, which VTK then choked on far
        # away from the cause.
        with pytest.raises(ValueError, match="cannot be sized"):
            extent_for(value)

    @pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
    def test_a_value_that_is_not_a_number_is_refused(self, value: float) -> None:
        with pytest.raises(ValueError, match="cannot be sized"):
            extent_for(value)

    def test_it_never_returns_something_that_is_not_finite(self) -> None:
        # The property that was actually violated, stated directly.
        for power in range(0, 38):
            assert math.isfinite(extent_for(10.0**power))


class TestGeometryStaysDrawable:
    """The point of the cap: what is accepted can actually be built."""

    def test_an_arrow_at_the_cap_has_finite_geometry(self) -> None:
        plotter = pv.Plotter(off_screen=True, window_size=(120, 90))
        try:
            vector = Vector(name="A", components=(MAX_COMPONENT, 0.0, 0.0))
            VectorActors(plotter).draw([vector], "A")
            points = np.concatenate(
                [actor.mapper.dataset.points for actor in [
                    plotter.renderer.actors["vector-A"]
                ]]
            )
            assert math.isfinite(float(np.abs(points).max()))
        finally:
            plotter.close()

    def test_the_scene_fits_a_vector_at_the_cap(self) -> None:
        vector = Vector(name="A", components=(MAX_COMPONENT, 0.0, 0.0))
        assert math.isfinite(extent_for_vectors([vector]))

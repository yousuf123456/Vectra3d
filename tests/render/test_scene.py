"""Scene extent rules (`interaction-spec.md` section 3).

Only the sizing maths is tested here. What the scene looks like is checked by
eye, because no test can tell whether a grid reads clearly.
"""

from __future__ import annotations

from itertools import islice

import pytest

from vectra3d.render.scene import (
    MIN_EXTENT,
    extent_for,
    extent_for_vectors,
    extent_steps,
)
from vectra3d.state.models import Vector


def test_the_sequence_starts_at_ten() -> None:
    assert list(islice(extent_steps(), 7)) == [10, 20, 50, 100, 200, 500, 1000]


def test_the_sequence_keeps_the_one_two_five_pattern() -> None:
    steps = list(islice(extent_steps(), 15))
    for step in steps:
        mantissa = step
        while mantissa >= 10:
            mantissa /= 10
        assert round(mantissa, 6) in (1, 2, 5), step


def test_the_sequence_only_grows() -> None:
    steps = list(islice(extent_steps(), 15))
    assert steps == sorted(steps)
    assert len(set(steps)) == len(steps)


@pytest.mark.parametrize(
    ("max_abs", "expected"),
    [
        (0.0, 10),  # an empty scene stays at the minimum
        (5.0, 10),
        (10.0, 10),  # exactly on the boundary still fits
        (10.5, 20),
        (20.0, 20),
        (21.0, 50),
        (100.0, 100),
        (101.0, 200),
        (1500.0, 2000),
    ],
)
def test_extent_for_a_distance(max_abs: float, expected: float) -> None:
    assert extent_for(max_abs) == expected


def test_the_world_never_shrinks_below_ten() -> None:
    assert extent_for(0.0) == MIN_EXTENT
    assert extent_for_vectors([]) == MIN_EXTENT


def test_the_largest_component_decides_the_extent() -> None:
    vectors = [
        Vector(name="A", components=(3.0, 4.0, 5.0)),
        Vector(name="B", components=(1.0, 45.0, 2.0)),
    ]
    assert extent_for_vectors(vectors) == 50


def test_a_negative_component_counts_as_far_as_a_positive_one() -> None:
    vectors = [Vector(name="A", components=(0.0, -45.0, 0.0))]
    assert extent_for_vectors(vectors) == 50


def test_removing_a_long_vector_lets_the_world_shrink_again() -> None:
    # The extent is worked out from what is there now, so shrinking needs no
    # separate rule: drop the long vector and the answer is small again.
    big = Vector(name="A", components=(0.0, 0.0, 300.0))
    small = Vector(name="B", components=(1.0, 2.0, 3.0))
    assert extent_for_vectors([big, small]) == 500
    assert extent_for_vectors([small]) == 10

"""Where a vector's letter is placed."""

from __future__ import annotations

import pytest

from vectra3d.render.vector_actor import LETTER_OFFSET, letter_position
from vectra3d.state.models import Vector


def test_the_letter_sits_just_past_the_head() -> None:
    vector = Vector(name="A", components=(10.0, 0.0, 0.0))
    assert letter_position(vector) == pytest.approx(
        (10.0 * (1 + LETTER_OFFSET), 0.0, 0.0)
    )


def test_the_offset_follows_the_vector_not_the_origin() -> None:
    # With a tail away from the origin, the letter must still sit past the
    # head along the vector's own line. Scaling the head outward from the
    # origin would put it somewhere else entirely. Every tail is the origin
    # in the MVP, but the data model stores one so free vectors can be added
    # later without rewriting this (`project-overview.md`).
    vector = Vector(name="A", components=(10.0, 0.0, 0.0), tail=(5.0, 5.0, 0.0))
    assert letter_position(vector) == pytest.approx(
        (15.0 + 10.0 * LETTER_OFFSET, 5.0, 0.0)
    )


def test_a_zero_vector_puts_its_letter_at_its_tail() -> None:
    # It has no direction to offset along, and no arrow either.
    vector = Vector(name="A", components=(0.0, 0.0, 0.0), tail=(1.0, 2.0, 3.0))
    assert letter_position(vector) == pytest.approx((1.0, 2.0, 3.0))

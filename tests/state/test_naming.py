"""Naming and color rules (`features.md`, global vector rules)."""

from __future__ import annotations

import pytest

from vectra3d.state import naming


def test_first_name_is_a() -> None:
    assert naming.next_free_name([]) == "A"


def test_names_are_handed_out_in_order() -> None:
    assert naming.next_free_name(["A"]) == "B"
    assert naming.next_free_name(["A", "B"]) == "C"


def test_lowest_free_name_is_reused() -> None:
    # B was deleted, so the next vector is B again, not D.
    assert naming.next_free_name(["A", "C"]) == "B"


def test_no_name_left_when_all_ten_are_used() -> None:
    assert naming.next_free_name(naming.NAMES) is None


def test_there_are_exactly_ten_names() -> None:
    assert len(naming.NAMES) == naming.MAX_VECTORS
    assert naming.NAMES[0] == "A"
    assert naming.NAMES[-1] == "J"


def test_every_name_has_its_own_color() -> None:
    assert len(naming.VECTOR_COLORS) == len(naming.NAMES)
    assert len(set(naming.VECTOR_COLORS)) == len(naming.VECTOR_COLORS)


def test_color_belongs_to_the_letter() -> None:
    # Derived from the name, so a reused letter comes back in its old color.
    assert naming.color_for("A") == naming.VECTOR_COLORS[0]
    assert naming.color_for("J") == naming.VECTOR_COLORS[9]


def test_unknown_name_has_no_color() -> None:
    with pytest.raises(KeyError):
        naming.color_for("K")


def test_no_vector_color_clashes_with_a_reserved_color() -> None:
    # Red, green and blue belong to the axes and the component vectors
    # (`interaction-spec.md` 2.1); near-black belongs to operation results.
    reserved = {"#FF0000", "#00FF00", "#0000FF", naming.RESULT_COLOR}
    assert not {c.upper() for c in naming.VECTOR_COLORS} & reserved


def test_no_vector_color_is_a_pure_axis_hue() -> None:
    # A color counts as an axis hue if one channel is strong and the other two
    # are near zero, which is what makes it read as "the red one" on screen.
    for color in naming.VECTOR_COLORS:
        r, g, b = (int(color[i : i + 2], 16) for i in (1, 3, 5))
        channels = sorted((r, g, b))
        assert not (channels[2] > 120 and channels[1] < 40), color

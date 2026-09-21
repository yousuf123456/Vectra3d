"""What each vector's card says (F-11 basic).

Only the text is tested, not the widgets: this is the part that has to match
the spec's display rules. No window is opened.
"""

from __future__ import annotations

from vectra3d.state.models import Vector
from vectra3d.ui.info_panel import card_values


def test_a_card_lists_the_three_components() -> None:
    vector = Vector(name="A", components=(3.0, 4.0, 5.0))
    assert card_values(vector) == [("x", "3.00"), ("y", "4.00"), ("z", "5.00")]


def test_values_are_shown_to_two_decimals() -> None:
    vector = Vector(name="A", components=(1.5, 2.0, 0.333))
    assert card_values(vector) == [("x", "1.50"), ("y", "2.00"), ("z", "0.33")]


def test_negative_components_keep_their_sign() -> None:
    vector = Vector(name="B", components=(-2.0, 0.0, -7.25))
    assert card_values(vector) == [("x", "-2.00"), ("y", "0.00"), ("z", "-7.25")]


def test_a_component_that_rounds_to_zero_is_never_negative_zero() -> None:
    # Typing r=1, theta=90, phi=90 leaves x as 6.1e-17, and the sign of such
    # a value is an accident of floating point, not something to show.
    vector = Vector(name="C", components=(-1e-17, 1.0, 0.0))
    assert card_values(vector)[0] == ("x", "0.00")


def test_the_zero_vector_still_gets_a_card() -> None:
    # It has no arrow to draw, so the card is the only place it appears.
    vector = Vector(name="D", components=(0.0, 0.0, 0.0))
    assert card_values(vector) == [("x", "0.00"), ("y", "0.00"), ("z", "0.00")]

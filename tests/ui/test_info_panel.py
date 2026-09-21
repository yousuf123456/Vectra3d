"""What each vector's card says (F-11 basic, then full at G2.3).

Only the text is tested, not the widgets: this is the part that has to match
the spec's display rules. No window is opened.

`card_values` returns two columns. The left is what the vector is - its
components and its magnitude - and the right is which way it points: the
three direction angles and the unit vector.
"""

from __future__ import annotations

from vectra3d.core.formatting import EM_DASH, UNDEFINED_NOTE
from vectra3d.state.models import Vector
from vectra3d.ui.info_panel import card_note, card_values


def left_of(vector: Vector) -> list[tuple[str, str]]:
    return card_values(vector)[0]


def right_of(vector: Vector) -> list[tuple[str, str]]:
    return card_values(vector)[1]


# --- Components: the F-11 basic rules, unchanged by G2.3 ---


def test_a_card_lists_the_three_components() -> None:
    vector = Vector(name="A", components=(3.0, 4.0, 5.0))
    assert left_of(vector)[:3] == [("x", "3.00"), ("y", "4.00"), ("z", "5.00")]


def test_values_are_shown_to_two_decimals() -> None:
    vector = Vector(name="A", components=(1.5, 2.0, 0.333))
    assert left_of(vector)[:3] == [("x", "1.50"), ("y", "2.00"), ("z", "0.33")]


def test_negative_components_keep_their_sign() -> None:
    vector = Vector(name="B", components=(-2.0, 0.0, -7.25))
    assert left_of(vector)[:3] == [("x", "-2.00"), ("y", "0.00"), ("z", "-7.25")]


def test_a_component_that_rounds_to_zero_is_never_negative_zero() -> None:
    # Typing r=1, theta=90, phi=90 leaves x as 6.1e-17, and the sign of such
    # a value is an accident of floating point, not something to show.
    vector = Vector(name="C", components=(-1e-17, 1.0, 0.0))
    assert left_of(vector)[0] == ("x", "0.00")


def test_the_zero_vector_still_gets_a_card() -> None:
    # It has no arrow to draw, so the card is the only place it appears.
    vector = Vector(name="D", components=(0.0, 0.0, 0.0))
    assert left_of(vector)[:3] == [("x", "0.00"), ("y", "0.00"), ("z", "0.00")]


# --- Magnitude, angles and the unit vector (F-11 full) ---


def test_magnitude_closes_the_left_column() -> None:
    vector = Vector(name="A", components=(3.0, 4.0, 0.0))
    assert left_of(vector)[-1] == ("|v|", "5.00")


def test_the_right_column_is_three_angles_then_the_unit_vector() -> None:
    vector = Vector(name="A", components=(5.0, 0.0, 0.0))
    assert right_of(vector) == [
        ("α", "0.00°"),
        ("β", "90.00°"),
        ("γ", "90.00°"),
        ("û", "(1.00, 0.00, 0.00)"),
    ]


def test_angles_carry_the_degree_sign_and_two_decimals() -> None:
    # (3, 4, 5): |v| = 7.0710678..., so cos a = 3/7.07 and gamma is exactly 45.
    vector = Vector(name="A", components=(3.0, 4.0, 5.0))
    assert right_of(vector)[:3] == [
        ("α", "64.90°"),
        ("β", "55.55°"),
        ("γ", "45.00°"),
    ]


def test_the_unit_vector_is_one_value_not_three() -> None:
    # It is read as a direction rather than three separate quantities, and
    # three more rows would not fit the panel.
    vector = Vector(name="A", components=(3.0, 4.0, 5.0))
    assert right_of(vector)[-1] == ("û", "(0.42, 0.57, 0.71)")


def test_both_columns_are_the_same_height() -> None:
    # They are laid out side by side, so a mismatch would leave a card with
    # a ragged bottom edge.
    vector = Vector(name="A", components=(1.0, 2.0, 2.0))
    left, right = card_values(vector)
    assert len(left) == len(right)


# --- The zero vector has no direction (interaction-spec.md 2.4) ---


def test_the_zero_vector_shows_dashes_for_everything_undefined() -> None:
    vector = Vector(name="D", components=(0.0, 0.0, 0.0))
    assert [text for _, text in right_of(vector)] == [EM_DASH] * 4


def test_the_zero_vector_still_shows_a_magnitude_of_zero() -> None:
    # Its length is genuinely zero, which is a number. Only the direction is
    # undefined, so only the direction is dashed.
    vector = Vector(name="D", components=(0.0, 0.0, 0.0))
    assert left_of(vector)[-1] == ("|v|", "0.00")


def test_the_zero_vector_card_explains_its_dashes() -> None:
    vector = Vector(name="D", components=(0.0, 0.0, 0.0))
    assert card_note(vector) == UNDEFINED_NOTE


def test_an_ordinary_card_has_no_note() -> None:
    vector = Vector(name="A", components=(3.0, 4.0, 5.0))
    assert card_note(vector) is None


# --- Lock status (shown here, set from G2.5) ---


def test_a_vector_is_unlocked_unless_said_otherwise() -> None:
    assert Vector(name="A", components=(1.0, 0.0, 0.0)).locked is False


def test_a_vector_can_be_locked() -> None:
    # Nothing sets this until F-09a in G2.5; the card already honours it.
    vector = Vector(name="A", components=(1.0, 0.0, 0.0), locked=True)
    assert vector.locked is True

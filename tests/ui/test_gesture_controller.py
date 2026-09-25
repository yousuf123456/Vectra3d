"""Creating a vector by hand, fed with intents (F-03, `interaction-spec.md` 6.2).

The controller has no Qt of its own, so these run without a window. The
camera is looking along +y with z up, so the screen's right is +x.
"""

from __future__ import annotations

from vectra3d.gestures.intents import (
    BeginSteer,
    BeginTwoHand,
    Commit,
    TwoHandKind,
    UpdateTwoHand,
)
from vectra3d.state import actions, naming
from vectra3d.state.store import VectorStore
from vectra3d.ui.action_panel import LIMIT_TEXT
from vectra3d.ui.gesture_controller import GestureController

LOOKING_ALONG_Y = (0.0, 1.0, 0.0)
Z_UP = (0.0, 0.0, 1.0)

# Scale 0.25, pinch points 0.125 apart: 0.5 hs, well inside "hands together".
START = ((0.5, 0.5), (0.625, 0.5))
BEGIN = BeginTwoHand(TwoHandKind.CREATE, (0, 1), START, 0.25)
# Hand 1 pulled 1.0 right: 4.5 hs apart, (4.5 - 0.5) / 8 * 25 = 12.5 along +x.
PULLED = UpdateTwoHand(((0.5, 0.5), (1.625, 0.5)), 0.25)
# Pulled 0.03125 more than the start: 0.125 hs, 0.125 / 8 * 25 = 0.390625 long.
NUDGED = UpdateTwoHand(((0.5, 0.5), (0.65625, 0.5)), 0.25)
# Pulled only 0.001: 0.004 hs, 0.0125 long - under the 0.1 minimum.
BARELY = UpdateTwoHand(((0.5, 0.5), (0.626, 0.5)), 0.25)


def run(controller: GestureController, *intents) -> None:
    controller.apply(intents, LOOKING_ALONG_Y, Z_UP)


def test_a_vector_appears_as_soon_as_the_gesture_begins() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, BEGIN)
    assert store.names == ("A",)
    assert store.active_name == "A"
    assert store.gesture_in_progress


def test_the_vector_follows_the_hands_live() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, BEGIN, NUDGED)
    assert store.get("A").components == (0.390625, 0.0, 0.0)
    run(controller, PULLED)
    assert store.get("A").components == (12.5, 0.0, 0.0)


def test_the_label_shows_the_live_magnitude_while_creating() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, BEGIN, PULLED)
    assert controller.labels() == {"A": "|A| = 12.50"}


def test_releasing_keeps_the_vector_as_one_undo_step() -> None:
    store = VectorStore()
    actions.create_vector(store, (0.0, 3.0, 0.0))
    controller = GestureController(store)
    run(controller, BEGIN, NUDGED, PULLED, Commit())

    assert store.get("B").components == (12.5, 0.0, 0.0)
    assert store.active_name == "B"
    assert not store.gesture_in_progress
    # Back to its letter once confirmed.
    assert controller.labels() == {}

    actions.undo(store)
    assert store.names == ("A",)
    assert store.active_name == "A"


def test_the_next_vector_gets_the_lowest_free_letter() -> None:
    store = VectorStore()
    for _ in range(3):
        actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.delete_vector(store, "B")
    controller = GestureController(store)
    run(controller, BEGIN, PULLED, Commit())
    assert store.names == ("A", "B", "C")
    assert store.get("B").components == (12.5, 0.0, 0.0)


def test_a_vector_too_short_on_release_is_not_created() -> None:
    store = VectorStore()
    controller = GestureController(store)
    run(controller, BEGIN, BARELY, Commit())
    assert store.names == ()
    assert not store.history.can_undo
    assert not store.gesture_in_progress


def test_at_ten_vectors_nothing_is_drawn_and_the_student_is_told() -> None:
    store = VectorStore()
    for _ in range(naming.MAX_VECTORS):
        actions.create_vector(store, (1.0, 0.0, 0.0))
    before = store.snapshot()
    controller = GestureController(store)

    run(controller, BEGIN, PULLED, Commit())

    assert controller.message == LIMIT_TEXT
    assert store.snapshot() == before
    assert not store.gesture_in_progress
    # No step was added: one undo takes back the tenth create, not a gesture.
    actions.undo(store)
    assert store.count == naming.MAX_VECTORS - 1


def test_the_message_goes_when_the_next_gesture_begins() -> None:
    store = VectorStore()
    for _ in range(naming.MAX_VECTORS):
        actions.create_vector(store, (1.0, 0.0, 0.0))
    controller = GestureController(store)
    run(controller, BEGIN, Commit())
    assert controller.message == LIMIT_TEXT

    run(controller, BeginSteer(0, (0.5, 0.5), 0.25))
    assert controller.message is None


def test_a_resize_does_not_create_anything_yet() -> None:
    # Resizing is G5.4; until then its intents change nothing.
    store = VectorStore()
    controller = GestureController(store)
    resize = BeginTwoHand(TwoHandKind.RESIZE, (0, 1), START, 0.25)
    run(controller, resize, PULLED, Commit())
    assert store.names == ()
    assert not store.gesture_in_progress

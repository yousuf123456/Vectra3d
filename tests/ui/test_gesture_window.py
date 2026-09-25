"""Creating by hand, through the real window (F-03, `interaction-spec.md` 3, 6.2).

What only the window can get wrong: that a frame's intents reach the
controller with the camera's directions, that the scene does not rescale
while a vector is being pulled, that undo is out of reach mid-gesture, and
that a refused gesture's message reaches the camera preview.
"""

from __future__ import annotations

import numpy as np
import pytest

from vectra3d.gestures.hand_frame import NO_GESTURE, Hand, HandFrame
from vectra3d.gestures.intents import (
    BeginSteer,
    BeginTwoHand,
    Cancel,
    Commit,
    TwoHandKind,
    UpdateSteer,
    UpdateTwoHand,
)

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.state import actions, naming  # noqa: E402
from vectra3d.state.store import VectorStore  # noqa: E402
from vectra3d.ui.action_panel import LIMIT_TEXT  # noqa: E402
from vectra3d.ui.main_window import VectraMainWindow  # noqa: E402

ASPECT = 4 / 3
PIXELS = np.zeros((480, 640, 3), dtype=np.uint8)

START = ((0.5, 0.5), (0.625, 0.5))
BEGIN = BeginTwoHand(TwoHandKind.CREATE, (0, 1), START, 0.25)
# 12.5 long: past the starting extent of 10, so the scene will have to grow.
PULLED = UpdateTwoHand(((0.5, 0.5), (1.625, 0.5)), 0.25)


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app: QApplication):
    window = VectraMainWindow(VectorStore())
    yield window
    window.close()


def apply(window: VectraMainWindow, *intents, now_ms: int = 0) -> None:
    camera = window.plotter.camera
    window._gesture_controller.apply(intents, camera.direction, camera.up, now_ms)


def pinching_hand_at(x: float) -> Hand:
    """A pinching hand, 1 hs = 0.2 picture heights, fingertips at `x`."""
    points = [(x, 0.5)] * 21
    points[0] = (x, 0.8)
    points[9] = (x, 0.6)
    points[4] = (x, 0.40)
    points[8] = (x, 0.42)
    return Hand(landmarks=tuple(points), gesture=NO_GESTURE, gesture_score=0.9)


def test_two_hands_pinching_together_start_a_vector(window) -> None:
    # Pinch points 0.1 of the width apart: 0.13 picture heights, 0.67 hs -
    # hands together, so this is a create.
    both = (pinching_hand_at(0.45), pinching_hand_at(0.55))
    window._on_hand_frame(PIXELS, HandFrame(hands=both, timestamp_ms=0, aspect=ASPECT))
    assert window._store.names == ("A",)
    assert window._store.gesture_in_progress


def test_the_scene_does_not_rescale_until_the_gesture_is_released(window) -> None:
    assert window.scene.extent == 10
    apply(window, BEGIN, PULLED)
    assert window._store.active.components[0] != 0.0
    assert window.scene.extent == 10

    apply(window, Commit())
    assert window.scene.extent == 20


def test_undo_is_out_of_reach_during_a_gesture(window) -> None:
    actions.create_vector(window._store, (1.0, 0.0, 0.0))
    assert window._undo.isEnabled()

    apply(window, BEGIN, PULLED)
    assert not window._undo.isEnabled()
    assert not window._redo.isEnabled()

    apply(window, Commit())
    assert window._undo.isEnabled()


def test_the_limit_message_reaches_the_camera_preview(window) -> None:
    for _ in range(naming.MAX_VECTORS):
        actions.create_vector(window._store, (1.0, 0.0, 0.0))
    both = (pinching_hand_at(0.45), pinching_hand_at(0.55))
    window._on_hand_frame(PIXELS, HandFrame(hands=both, timestamp_ms=0, aspect=ASPECT))
    assert window._store.count == naming.MAX_VECTORS
    assert window.camera_preview.status.endswith(LIMIT_TEXT)


# --- Redrawing only what moves ---


def test_mid_gesture_only_the_moving_vectors_card_changes(app, window) -> None:
    actions.create_vector(window._store, (1.0, 0.0, 0.0))
    # Beginning rebuilds the list once, as any new vector does: B needs a
    # card, and the highlight moves from A to B.
    apply(window, BEGIN)
    card_a = window.info_panel._card_by_name["A"]
    card_b = window.info_panel._card_by_name["B"]
    apply(window, PULLED)
    app.processEvents()

    # The same card widgets, not a rebuilt list...
    assert window.info_panel._card_by_name["A"] is card_a
    assert window.info_panel._card_by_name["B"] is card_b
    # ...with B's numbers brought up to date in place. The window's camera is
    # the default raised front-right view, so the pull is not along one axis;
    # its length is 12.5 whichever way it points. |v| is the fourth value.
    texts = [label.text() for label in card_b.value_labels]
    assert texts[3] == "12.50"


def test_the_zero_vector_note_goes_as_the_vector_grows(app, window) -> None:
    apply(window, BEGIN)
    card = window.info_panel._card_by_name["A"]
    assert not card.note_label.isHidden()

    apply(window, PULLED)
    app.processEvents()
    assert card.note_label.isHidden()


def test_frames_that_arrive_together_share_one_redraw(app, window) -> None:
    apply(window, BEGIN)
    calls = []
    original = window.vectors.redraw
    window.vectors.redraw = lambda *args: (calls.append(args), original(*args))

    nudged = UpdateTwoHand(((0.5, 0.5), (0.75, 0.5)), 0.25)
    apply(window, nudged)
    apply(window, PULLED)
    app.processEvents()

    # One redraw, of the latest position.
    assert len(calls) == 1
    assert calls[0][0] == window._store.get("A")
    assert calls[0][2] == "|A| = 12.50"


def test_after_release_the_whole_scene_is_redrawn(app, window) -> None:
    apply(window, BEGIN, PULLED)
    app.processEvents()
    card = window.info_panel._card_by_name["A"]

    apply(window, Commit())
    # A full refresh rebuilds the list, as it always has.
    assert window.info_panel._card_by_name["A"] is not card


# --- Resizing (F-07) ---

RESIZE = BeginTwoHand(TwoHandKind.RESIZE, (0, 1), START, 0.25)


def test_a_resize_moves_the_result_and_its_card_in_place(app, window) -> None:
    store = window._store
    actions.create_vector(store, (3.0, 0.0, 4.0))
    actions.create_vector(store, (0.0, 1.0, 0.0))
    actions.toggle_selected(store, "A")
    actions.toggle_selected(store, "B")
    actions.compute_resultant(store)
    actions.set_active(store, "A")
    app.processEvents()

    apply(window, RESIZE)
    result_card = window.info_panel._result_card
    apply(window, PULLED)
    app.processEvents()

    # A is now (10.5, 0, 14), so A + B is (10.5, 1, 14): its card says so
    # without having been rebuilt. |v| is the fourth value.
    assert window.info_panel._result_card is result_card
    texts = [label.text() for label in result_card.value_labels]
    assert texts[:3] == ["10.50", "1.00", "14.00"]
    # And the arrow was drawn at the new value straight away, not gliding.
    assert window._result == store.result


def test_a_resize_rescales_the_scene_only_on_release(app, window) -> None:
    actions.create_vector(window._store, (3.0, 0.0, 4.0))
    assert window.scene.extent == 10

    apply(window, RESIZE, PULLED)
    app.processEvents()
    assert window.scene.extent == 10

    apply(window, Commit())
    assert window.scene.extent == 20


def test_a_refused_resize_is_explained_in_the_camera_strip(window) -> None:
    actions.create_vector(window._store, (3.0, 0.0, 4.0))
    actions.toggle_locked(window._store, "A")
    # Pinch points 0.3 of the width apart: 0.4 picture heights, 2 hs - a resize.
    both = (pinching_hand_at(0.35), pinching_hand_at(0.65))
    window._on_hand_frame(PIXELS, HandFrame(hands=both, timestamp_ms=0, aspect=ASPECT))
    assert window.camera_preview.status.endswith("Vector A is locked.")


# --- Steering (F-06) and the angle arcs ---

STEER = BeginSteer(1, (0.5, 0.5), 0.25)
FULL_RIGHT = UpdateSteer((0.875, 0.5), 0.25)


def arcs_shown(window) -> bool:
    return "arc-theta" in window.plotter.actors and "arc-phi" in window.plotter.actors


def test_the_active_vector_always_shows_its_angles(app, window) -> None:
    # The user's request at G5.5: not only while steering.
    assert not arcs_shown(window)
    actions.create_vector(window._store, (0.0, -5.0, 3.0))
    assert arcs_shown(window)

    actions.delete_vector(window._store, "A")
    assert not arcs_shown(window)


def test_the_arcs_follow_the_vector_while_it_is_steered(app, window) -> None:
    actions.create_vector(window._store, (0.0, -5.0, 3.0))
    drawn = []
    original = window.angle_arcs.draw
    window.angle_arcs.draw = lambda vector: (drawn.append(vector), original(vector))

    apply(window, STEER, now_ms=0)
    apply(window, FULL_RIGHT, now_ms=500)
    app.processEvents()

    assert drawn[-1] == window._store.get("A")
    assert drawn[-1].components != (0.0, -5.0, 3.0)
    assert arcs_shown(window)


def test_the_arcs_move_to_whichever_vector_is_active(app, window) -> None:
    actions.create_vector(window._store, (0.0, -5.0, 3.0))
    actions.create_vector(window._store, (4.0, 0.0, 0.0))
    drawn = []
    original = window.angle_arcs.draw
    window.angle_arcs.draw = lambda vector: (drawn.append(vector), original(vector))

    actions.set_active(window._store, "A")
    assert drawn[-1].name == "A"


def test_a_cancelled_steer_puts_the_vector_and_its_arcs_back(app, window) -> None:
    actions.create_vector(window._store, (0.0, -5.0, 3.0))
    apply(window, STEER, now_ms=0)
    apply(window, FULL_RIGHT, now_ms=500)
    app.processEvents()
    apply(window, Cancel(), now_ms=533)
    assert window._store.get("A").components == (0.0, -5.0, 3.0)
    assert arcs_shown(window)


def test_the_arcs_hide_while_the_head_to_tail_animation_plays(app, window) -> None:
    store = window._store
    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.create_vector(store, (0.0, 1.0, 0.0))
    actions.toggle_selected(store, "A")
    actions.toggle_selected(store, "B")
    actions.compute_resultant(store)
    assert arcs_shown(window)

    window._play_head_to_tail()
    assert not arcs_shown(window)
    window._head_to_tail.cancel()
    assert arcs_shown(window)


def test_steering_rescales_the_scene_only_on_release(app, window) -> None:
    # (0, -12, 0) needs an extent of 20. Turned 45 degrees it is about
    # (8.49, -8.49, 0), which fits in 10 - but only once the steer ends.
    actions.create_vector(window._store, (0.0, -12.0, 0.0))
    window.scene.set_view("Front")
    assert window.scene.extent == 20

    apply(window, STEER, now_ms=0)
    apply(window, FULL_RIGHT, now_ms=500)
    app.processEvents()
    assert window.scene.extent == 20

    apply(window, Commit(), now_ms=533)
    assert window.scene.extent == 10

"""One gesture is one undo step, from raw hand frames (F-19, spec section 5).

The gesture session in `state/actions.py` and each gesture's commit are
tested with intents elsewhere. These go the whole way a real student does:
hand frames into the window's frame slot, through the hand metrics and the
gesture state machine, into the controller and the store. That is the only
place some of the cases below can happen at all - a hand that leaves the
picture, a gesture three hundred frames long.

Hands are synthetic: a wrist and a middle-finger base 0.2 picture heights
apart, so 1 hs is 0.2, with the thumb and index tips together for a pinch
and far apart for an open hand.
"""

from __future__ import annotations

import numpy as np
import pytest

from vectra3d.gestures.hand_frame import NO_GESTURE, Hand, HandFrame

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.state import actions  # noqa: E402
from vectra3d.state.store import VectorStore  # noqa: E402
from vectra3d.ui.main_window import VectraMainWindow  # noqa: E402

ASPECT = 4 / 3
PIXELS = np.zeros((480, 640, 3), dtype=np.uint8)
FRAME_MS = 33


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app: QApplication):
    window = VectraMainWindow(VectorStore())
    yield window
    window.close()


def hand(x: float, pinching: bool = True, gesture: str = NO_GESTURE) -> Hand:
    """A hand upright at `x` across the picture."""
    points = [(x, 0.5)] * 21
    points[0] = (x, 0.8)  # wrist
    points[9] = (x, 0.6)  # middle-finger base: 1 hs = 0.2
    if pinching:
        points[4], points[8] = (x, 0.40), (x, 0.42)  # 0.1 hs apart
    else:
        points[4], points[8] = (x - 0.08, 0.45), (x, 0.30)  # about 0.8 hs
    return Hand(landmarks=tuple(points), gesture=gesture, gesture_score=0.9)


class Hands:
    """Feeds frames to the window, one camera frame apart."""

    def __init__(self, window: VectraMainWindow) -> None:
        self._window = window
        self.now_ms = 0

    def show(self, *hands: Hand, frames: int = 1) -> None:
        for _ in range(frames):
            frame = HandFrame(hands=hands, timestamp_ms=self.now_ms, aspect=ASPECT)
            self._window._on_hand_frame(PIXELS, frame)
            self.now_ms += FRAME_MS

    def pull_apart(self, start: tuple[float, float], end: tuple[float, float]) -> None:
        """Both hands pinching, moving from `start` to `end` over 30 frames."""
        for step in range(31):
            t = step / 30
            left = start[0] + (end[0] - start[0]) * t
            right = start[1] + (end[1] - start[1]) * t
            self.show(hand(left), hand(right))

    def steer(self, x: float, to: float, frames: int, *others: Hand) -> None:
        """One hand pinching at `x`, waiting out the two-hand window, then
        pushed to `to` and held there for `frames` frames."""
        self.show(hand(x), *others, frames=20)  # 0.66 s: past the 0.5 s window
        self.show(hand(to), *others, frames=frames)

    def let_go(self, *xs: float) -> None:
        self.show(*(hand(x, pinching=False) for x in xs), frames=3)


def create(hands: Hands) -> None:
    """Pinch with both hands close together, pull apart, let go."""
    hands.pull_apart((0.45, 0.55), (0.25, 0.75))
    hands.let_go(0.25, 0.75)


# --- Every gesture is one step ---


def test_a_created_vector_goes_in_one_undo(window) -> None:
    store = window._store
    before = store.snapshot()
    create(Hands(window))

    assert store.names == ("A",)
    assert not store.gesture_in_progress
    assert actions.undo(store)
    assert store.snapshot() == before
    assert not store.history.can_undo


def test_a_resize_goes_in_one_undo(window) -> None:
    store = window._store
    actions.create_vector(store, (3.0, 0.0, 4.0))
    before = store.snapshot()

    hands = Hands(window)
    # Pinch points 0.5 of the width apart: 3.3 hs, so a resize.
    hands.pull_apart((0.25, 0.75), (0.15, 0.85))
    hands.let_go(0.15, 0.85)

    # Resized, not a second vector created.
    assert store.names == ("A",)
    assert store.snapshot() != before
    actions.undo(store)
    assert store.snapshot() == before


def test_a_steer_goes_in_one_undo(window) -> None:
    store = window._store
    actions.create_vector(store, (3.0, -4.0, 1.0))
    before = store.snapshot()

    hands = Hands(window)
    hands.steer(0.4, 0.7, frames=30)
    hands.let_go(0.7)

    assert store.snapshot() != before
    actions.undo(store)
    assert store.snapshot() == before


# --- Cases only real hand sequences produce ---


def test_losing_both_hands_mid_create_keeps_it_as_one_step(window) -> None:
    # Section 4.4: a hand lost for more than 0.3 s ends the gesture as a
    # normal release, not a cancel.
    store = window._store
    hands = Hands(window)
    hands.pull_apart((0.45, 0.55), (0.25, 0.75))
    hands.show(frames=15)  # half a second with no hands in the picture

    assert not store.gesture_in_progress
    assert store.names == ("A",)
    actions.undo(store)
    assert store.names == ()


def test_a_long_steer_leaves_the_earlier_history_alone(window) -> None:
    # Three hundred frames would fill the twenty-step history fifteen times
    # over if each were recorded.
    store = window._store
    for i in range(5):
        actions.create_vector(store, (1.0 + i, -2.0, 0.5))
    after_panel = store.snapshot()

    hands = Hands(window)
    hands.steer(0.4, 0.6, frames=300)
    hands.let_go(0.6)
    assert store.snapshot() != after_panel

    actions.undo(store)
    assert store.snapshot() == after_panel
    for _ in range(5):
        assert actions.undo(store)
    assert store.names == ()


def test_a_gesture_after_an_undo_clears_the_redo_history(window) -> None:
    store = window._store
    actions.create_vector(store, (1.0, 2.0, 3.0))
    actions.create_vector(store, (-2.0, 1.0, 0.5))
    actions.undo(store)
    assert store.history.can_redo

    create(Hands(window))

    assert not store.history.can_redo


def test_an_open_palm_from_the_free_hand_records_nothing(window) -> None:
    store = window._store
    actions.create_vector(store, (3.0, -4.0, 1.0))
    before = store.snapshot()
    free = hand(0.85, pinching=False, gesture="Open_Palm")

    hands = Hands(window)
    hands.steer(0.3, 0.55, frames=15)
    # It really was turning when the palm came.
    assert store.get("A").components != (3.0, -4.0, 1.0)
    hands.show(hand(0.55), free, frames=3)

    assert not store.gesture_in_progress
    assert store.snapshot() == before
    # Only the panel's create to take back.
    actions.undo(store)
    assert not store.history.can_undo


def test_undo_puts_back_a_result_the_gesture_moved_too(window) -> None:
    store = window._store
    actions.create_vector(store, (3.0, -4.0, 1.0))
    actions.create_vector(store, (0.0, 1.0, 2.0))
    actions.toggle_selected(store, "A")
    actions.toggle_selected(store, "B")
    actions.compute_resultant(store)
    actions.set_active(store, "A")
    before_result = store.result

    hands = Hands(window)
    hands.steer(0.4, 0.7, frames=30)
    hands.let_go(0.7)
    assert store.result.components != before_result.components

    actions.undo(store)
    assert store.result == before_result

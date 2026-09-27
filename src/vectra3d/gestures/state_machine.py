"""The gesture state machine (`interaction-spec.md` section 5).

Takes the measured hands of each frame and decides which gesture, if any, is
happening. Only one gesture happens at a time. The machine outputs intents
(`intents.py`) and never touches a vector.

The spec's five states, plus one short phase inside them:
- **WAITING** - one hand has just pinched. For up to the two-hand window it
  is not yet known whether this is steering or the start of a two-hand
  gesture, so nothing begins until the second hand pinches or the window
  runs out.

Letting go of a pinch commits at once. Only steering can be cancelled, by an
open palm from the free hand: a hand that has just let go of a pinch opens
naturally, and MediaPipe reads that as an open palm, so a palm seen after a
release says nothing about what the student meant (found with real hands at
G5.3).

A gesture begins only when a pinch *begins*. A pinch held through the end of a
gesture, or ignored because another gesture was running, starts nothing until
that hand lets go and pinches again.

Every timing comes from the frames' own timestamps, never the wall clock, so
the tests can play any sequence of frames at any pace.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from vectra3d import config
from vectra3d.gestures.hand_metrics import TrackedHand, average_scale, distance
from vectra3d.gestures.intents import (
    BeginSteer,
    BeginTwoHand,
    Cancel,
    Commit,
    HoldTriggered,
    Intent,
    TwoHandKind,
    UpdateSteer,
    UpdateTwoHand,
)

OPEN_PALM = "Open_Palm"
# The hold gestures of section 7, by MediaPipe's labels. What each one does
# is decided in `ui/gesture_controller.py`.
POINTING_UP = "Pointing_Up"
THUMB_UP = "Thumb_Up"
VICTORY = "Victory"
HOLD_GESTURES = (POINTING_UP, THUMB_UP, VICTORY)


def _ms(seconds: float) -> int:
    return round(seconds * 1000)


# Timestamps are whole milliseconds, so every timing is compared in them.
# Comparing float seconds would land a hair either side of a boundary
# depending on the numbers involved (0.334 - 0.034 is not exactly 0.3).
TWO_HAND_WINDOW_MS = _ms(config.TWO_HAND_PINCH_WINDOW_S)
HAND_LOST_MS = _ms(config.HAND_LOST_TIMEOUT_S)
HOLD_MS = _ms(config.HOLD_DURATION_S)


class GestureState(Enum):
    IDLE = "idle"
    WAITING = "waiting"
    CREATING = "creating"
    RESIZING = "resizing"
    STEERING = "steering"
    HOLDING = "holding"


@dataclass(frozen=True)
class HoldStatus:
    """A hold in progress: which gesture, by which hand, and how far to
    triggering, 0 to 1. The hand is so the preview can draw the progress
    ring around it (`interaction-spec.md` section 7)."""

    gesture: str
    progress: float
    hand_id: int


@dataclass(frozen=True)
class MachineOutput:
    """What one frame did: the state now, what to do, and any hold running."""

    state: GestureState
    intents: tuple[Intent, ...]
    hold: HoldStatus | None


class GestureStateMachine:
    """Call `update` once per frame, in order, with that frame's hands."""

    def __init__(self) -> None:
        self._state = GestureState.IDLE
        # Pinch state per hand as last seen, to spot a pinch beginning. A hand
        # out of view keeps its entry until the hand-lost timeout, so one that
        # comes back still pinching is not taken for a new pinch.
        self._was_pinching: dict[int, bool] = {}
        self._last_seen_ms: dict[int, int] = {}
        # A hand whose hold has triggered, and the gesture it used. It cannot
        # trigger again until it shows a different shape.
        self._spent: dict[int, str] = {}

        # The gesture in progress.
        self._hand_ids: tuple[int, ...] = ()
        self._started_ms = 0
        self._anchor = (0.0, 0.0)
        self._anchor_scale = 0.0
        self._hold_gesture = ""

    @property
    def state(self) -> GestureState:
        return self._state

    def update(self, hands: tuple[TrackedHand, ...], now_ms: int) -> MachineOutput:
        """Advance by one frame. `now_ms` is the frame's own timestamp."""
        by_id = {hand.hand_id: hand for hand in hands}
        onsets = [
            hand
            for hand in hands
            if hand.pinching and not self._was_pinching.get(hand.hand_id, False)
        ]
        for hand in hands:
            if self._spent.get(hand.hand_id) not in (None, hand.gesture):
                del self._spent[hand.hand_id]

        intents: list[Intent] = []
        hold: HoldStatus | None = None
        if self._state == GestureState.IDLE:
            hold = self._idle(hands, onsets, now_ms, intents)
        elif self._state == GestureState.WAITING:
            self._waiting(by_id, onsets, now_ms, intents)
        elif self._state == GestureState.STEERING:
            self._steering(hands, by_id, now_ms, intents)
        elif self._state in (GestureState.CREATING, GestureState.RESIZING):
            self._two_hand(by_id, now_ms, intents)
        elif self._state == GestureState.HOLDING:
            hold = self._holding(hands, by_id, onsets, now_ms, intents)

        self._remember(hands, now_ms)
        return MachineOutput(self._state, tuple(intents), hold)

    def camera_lost(self) -> MachineOutput:
        """The camera has stopped: no more frames will come.

        Every hand is lost at once, so a pinch gesture in progress ends the
        way a lost hand ends one (section 4.4): as a normal release, never a
        cancel. Without this it could never end at all - a lost hand is only
        noticed on the frames that follow, and there are none - and the app
        would stay inside the gesture for good, with undo out of reach.
        A hold or a wait simply stops. Everything remembered about hands is
        forgotten.
        """
        intents: list[Intent] = []
        if self._state in (
            GestureState.CREATING,
            GestureState.RESIZING,
            GestureState.STEERING,
        ):
            self._end(Commit(), intents)
        self._state = GestureState.IDLE
        self._hand_ids = ()
        self._was_pinching.clear()
        self._last_seen_ms.clear()
        self._spent.clear()
        return MachineOutput(self._state, tuple(intents), None)

    # --- States ---

    def _idle(
        self,
        hands: tuple[TrackedHand, ...],
        onsets: list[TrackedHand],
        now_ms: int,
        intents: list[Intent],
    ) -> HoldStatus | None:
        if len(onsets) >= 2:
            self._begin_two_hand(onsets[0], onsets[1], intents)
        elif onsets:
            first = onsets[0]
            self._state = GestureState.WAITING
            self._hand_ids = (first.hand_id,)
            self._started_ms = now_ms
            self._anchor = first.pinch_point
            self._anchor_scale = first.scale
        else:
            return self._start_hold(hands, now_ms)
        return None

    def _waiting(
        self,
        by_id: dict[int, TrackedHand],
        onsets: list[TrackedHand],
        now_ms: int,
        intents: list[Intent],
    ) -> None:
        first = by_id.get(self._hand_ids[0])
        if first is None or not first.pinching:
            # Let go, or gone, before anything began: nothing to undo.
            self._state = GestureState.IDLE
            return
        second = next((h for h in onsets if h.hand_id != first.hand_id), None)
        if second is not None and now_ms - self._started_ms <= TWO_HAND_WINDOW_MS:
            self._begin_two_hand(first, second, intents)
        elif now_ms - self._started_ms > TWO_HAND_WINDOW_MS:
            self._state = GestureState.STEERING
            intents.append(BeginSteer(first.hand_id, self._anchor, self._anchor_scale))
            intents.append(UpdateSteer(first.pinch_point, first.scale))

    def _steering(
        self,
        hands: tuple[TrackedHand, ...],
        by_id: dict[int, TrackedHand],
        now_ms: int,
        intents: list[Intent],
    ) -> None:
        # Only the free hand cancels, and only while it is not pinching. The
        # steering hand itself opens as it lets go, which MediaPipe reads as
        # an open palm (G5.3); and a pinch with the other three fingers
        # stretched out is read as one too (G5.2: three false cancels in 30 s).
        steering_id = self._hand_ids[0]
        if any(
            hand.hand_id != steering_id
            and hand.gesture == OPEN_PALM
            and not hand.pinching
            for hand in hands
        ):
            self._end(Cancel(), intents)
            return
        hand = by_id.get(steering_id)
        if hand is None:
            self._while_missing(now_ms, intents)
        elif not hand.pinching:
            self._end(Commit(), intents)
        else:
            intents.append(UpdateSteer(hand.pinch_point, hand.scale))

    def _two_hand(
        self,
        by_id: dict[int, TrackedHand],
        now_ms: int,
        intents: list[Intent],
    ) -> None:
        # No open-palm cancel here. Both hands are pinching, so a palm could
        # only come from a hand that has just let go - which is a release.
        first, second = (by_id.get(hand_id) for hand_id in self._hand_ids)
        if first is None or second is None:
            self._while_missing(now_ms, intents)
        elif not (first.pinching and second.pinching):
            self._end(Commit(), intents)
        else:
            intents.append(
                UpdateTwoHand(
                    (first.pinch_point, second.pinch_point),
                    average_scale(first, second),
                )
            )

    def _holding(
        self,
        hands: tuple[TrackedHand, ...],
        by_id: dict[int, TrackedHand],
        onsets: list[TrackedHand],
        now_ms: int,
        intents: list[Intent],
    ) -> HoldStatus | None:
        if onsets:
            # A pinch outranks a hold: drop the hold and treat this frame as
            # if nothing had been happening.
            self._state = GestureState.IDLE
            return self._idle(hands, onsets, now_ms, intents)

        hand = by_id.get(self._hand_ids[0])
        if hand is None or not _holds(hand, self._hold_gesture):
            # The hand changed shape, dipped below the confidence, or left.
            self._state = GestureState.IDLE
            return None

        progress = (now_ms - self._started_ms) / HOLD_MS
        if progress < 1.0:
            return HoldStatus(self._hold_gesture, progress, hand.hand_id)
        self._spent[hand.hand_id] = self._hold_gesture
        intents.append(HoldTriggered(self._hold_gesture))
        self._state = GestureState.IDLE
        return None

    # --- Helpers ---

    def _start_hold(
        self, hands: tuple[TrackedHand, ...], now_ms: int
    ) -> HoldStatus | None:
        for hand in hands:
            if hand.gesture in HOLD_GESTURES and _holds(hand, hand.gesture):
                if self._spent.get(hand.hand_id) == hand.gesture:
                    continue
                self._state = GestureState.HOLDING
                self._hand_ids = (hand.hand_id,)
                self._hold_gesture = hand.gesture
                self._started_ms = now_ms
                return HoldStatus(hand.gesture, 0.0, hand.hand_id)
        return None

    def _begin_two_hand(
        self, first: TrackedHand, second: TrackedHand, intents: list[Intent]
    ) -> None:
        scale = average_scale(first, second)
        apart_hs = (
            distance(first.pinch_point, second.pinch_point) / scale
            if scale > 0
            else math.inf
        )
        kind = (
            TwoHandKind.CREATE
            if apart_hs < config.HANDS_TOGETHER_HS
            else TwoHandKind.RESIZE
        )
        self._state = (
            GestureState.CREATING if kind == TwoHandKind.CREATE else GestureState.RESIZING
        )
        self._hand_ids = (first.hand_id, second.hand_id)
        intents.append(
            BeginTwoHand(
                kind,
                (first.hand_id, second.hand_id),
                (first.pinch_point, second.pinch_point),
                scale,
            )
        )

    def _while_missing(self, now_ms: int, intents: list[Intent]) -> None:
        """A gesture hand is out of view: pause, and release once it is lost.

        Section 4.4: lost for more than the timeout ends the gesture as a
        normal release, never a cancel. Timed from when the hand was
        last seen; its entry is only forgotten after this check has run.
        """
        last_seen_ms = min(
            self._last_seen_ms[hand_id]
            for hand_id in self._hand_ids
            if hand_id in self._last_seen_ms
        )
        if now_ms - last_seen_ms > HAND_LOST_MS:
            self._end(Commit(), intents)

    def _end(self, intent: Intent, intents: list[Intent]) -> None:
        intents.append(intent)
        self._state = GestureState.IDLE
        self._hand_ids = ()

    def _remember(self, hands: tuple[TrackedHand, ...], now_ms: int) -> None:
        for hand in hands:
            self._was_pinching[hand.hand_id] = hand.pinching
            self._last_seen_ms[hand.hand_id] = now_ms
        for hand_id, seen_ms in list(self._last_seen_ms.items()):
            if now_ms - seen_ms > HAND_LOST_MS:
                del self._last_seen_ms[hand_id]
                del self._was_pinching[hand_id]
                self._spent.pop(hand_id, None)


def _holds(hand: TrackedHand, gesture: str) -> bool:
    return hand.gesture == gesture and hand.gesture_score >= config.HOLD_CONFIDENCE

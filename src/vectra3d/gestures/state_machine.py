"""The gesture state machine (`interaction-spec.md` section 5).

Takes the measured hands of each frame and decides which gesture, if any, is
happening. Only one gesture happens at a time. The machine outputs intents
(`intents.py`) and never touches a vector.

The spec's five states, plus two short phases inside them:
- **WAITING** - one hand has just pinched. For up to the two-hand window it
  is not yet known whether this is steering or the start of a two-hand
  gesture, so nothing begins until the second hand pinches or the window
  runs out.
- **RELEASING** - a pinch gesture's pinch has ended. The gesture is frozen and
  waits the release confirm window before committing, because the open palm
  that cancels it can only appear after the pinching hand has opened, which
  ends the pinch first.

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
# The hold gestures of section 7. What each one does is G5.8's business.
HOLD_GESTURES = ("Pointing_Up", "Thumb_Up", "Victory")


def _ms(seconds: float) -> int:
    return round(seconds * 1000)


# Timestamps are whole milliseconds, so every timing is compared in them.
# Comparing float seconds would land a hair either side of a boundary
# depending on the numbers involved (0.334 - 0.034 is not exactly 0.3).
TWO_HAND_WINDOW_MS = _ms(config.TWO_HAND_PINCH_WINDOW_S)
RELEASE_CONFIRM_MS = _ms(config.RELEASE_CONFIRM_S)
HAND_LOST_MS = _ms(config.HAND_LOST_TIMEOUT_S)
HOLD_MS = _ms(config.HOLD_DURATION_S)


class GestureState(Enum):
    IDLE = "idle"
    WAITING = "waiting"
    CREATING = "creating"
    RESIZING = "resizing"
    STEERING = "steering"
    RELEASING = "releasing"
    HOLDING = "holding"


@dataclass(frozen=True)
class HoldStatus:
    """A hold in progress: which gesture, and how far to triggering, 0 to 1."""

    gesture: str
    progress: float


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
        # Only a hand that is not pinching can cancel. A pinch with the other
        # three fingers stretched out is read as an open palm by MediaPipe's
        # classifier often enough to cancel gestures at random (measured with
        # real hands at G5.2: three false cancels in 30 s).
        palm = any(hand.gesture == OPEN_PALM and not hand.pinching for hand in hands)
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
            self._steering(by_id, palm, now_ms, intents)
        elif self._state in (GestureState.CREATING, GestureState.RESIZING):
            self._two_hand(by_id, palm, now_ms, intents)
        elif self._state == GestureState.RELEASING:
            self._releasing(palm, now_ms, intents)
        elif self._state == GestureState.HOLDING:
            hold = self._holding(hands, by_id, onsets, now_ms, intents)

        self._remember(hands, now_ms)
        return MachineOutput(self._state, tuple(intents), hold)

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
        by_id: dict[int, TrackedHand],
        palm: bool,
        now_ms: int,
        intents: list[Intent],
    ) -> None:
        if palm:
            self._end(Cancel(), intents)
            return
        hand = by_id.get(self._hand_ids[0])
        if hand is None:
            self._while_missing(now_ms, intents)
        elif not hand.pinching:
            self._begin_release(now_ms)
        else:
            intents.append(UpdateSteer(hand.pinch_point, hand.scale))

    def _two_hand(
        self,
        by_id: dict[int, TrackedHand],
        palm: bool,
        now_ms: int,
        intents: list[Intent],
    ) -> None:
        if palm:
            self._end(Cancel(), intents)
            return
        first, second = (by_id.get(hand_id) for hand_id in self._hand_ids)
        if first is None or second is None:
            self._while_missing(now_ms, intents)
        elif not (first.pinching and second.pinching):
            self._begin_release(now_ms)
        else:
            intents.append(
                UpdateTwoHand(
                    (first.pinch_point, second.pinch_point),
                    average_scale(first, second),
                )
            )

    def _releasing(self, palm: bool, now_ms: int, intents: list[Intent]) -> None:
        if palm:
            self._end(Cancel(), intents)
        elif now_ms - self._started_ms >= RELEASE_CONFIRM_MS:
            self._end(Commit(), intents)

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
            return HoldStatus(self._hold_gesture, progress)
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
                return HoldStatus(hand.gesture, 0.0)
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
        normal release. It commits at once, without the confirm window,
        because losing a hand is never a cancel. Timed from when the hand was
        last seen; its entry is only forgotten after this check has run.
        """
        last_seen_ms = min(
            self._last_seen_ms[hand_id]
            for hand_id in self._hand_ids
            if hand_id in self._last_seen_ms
        )
        if now_ms - last_seen_ms > HAND_LOST_MS:
            self._end(Commit(), intents)

    def _begin_release(self, now_ms: int) -> None:
        self._state = GestureState.RELEASING
        self._started_ms = now_ms

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

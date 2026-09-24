"""Turns each frame's raw hands into the measurements gestures are built on.

For every hand this works out, frame by frame (`interaction-spec.md` section 4):
- its **hand scale** (1 hs = wrist to the base of the middle finger), which
  every gesture distance is divided by, so gestures work the same leaning in
  or sitting back;
- the **pinch distance**, thumb tip to index tip, in hs;
- whether it is **pinching**, with a gap between the start and end
  thresholds so a pinch held near the edge does not flicker;
- the **pinch point**, halfway between the two fingertips.

Three things make this more than arithmetic:
- **Picture shape.** Landmarks are 0-1 across each side of the picture
  separately, so on a 4:3 picture one unit of x is a third longer than one of
  y. Every point is converted to units of picture height before anything is
  measured; without that a hand's scale would change by a third just by
  tilting it.
- **Smoothing.** The four landmarks used here pass through a One Euro filter
  (section 4.3), timed by each frame's own timestamp because the frame rate is
  not steady.
- **Which hand is which.** MediaPipe lists hands in no stable order, and
  smoothing and pinch state both belong to one particular hand. Each hand is
  matched to the nearest wrist in the previous frame and keeps an id while it
  stays in view. A hand that goes missing is forgotten at once; the grace
  period of section 4.4 belongs to the state machine (G5.2).

Pure logic: no Qt, OpenCV or MediaPipe, so it is tested with made-up hands.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import permutations

from vectra3d import config
from vectra3d.gestures.hand_frame import Hand, HandFrame

# MediaPipe's numbering of the hand points this module uses.
WRIST = 0
THUMB_TIP = 4
INDEX_TIP = 8
MIDDLE_BASE = 9
_USED_LANDMARKS = (WRIST, THUMB_TIP, INDEX_TIP, MIDDLE_BASE)

# A point in picture-height units: x runs 0 to the aspect ratio, y 0 to 1.
Point = tuple[float, float]


def to_picture_units(point: tuple[float, float], aspect: float) -> Point:
    """A 0-1 landmark in units of picture height, so x and y measure alike."""
    return (point[0] * aspect, point[1])


def distance(a: Point, b: Point) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def hand_scale(wrist: Point, middle_base: Point) -> float:
    """1 hs: the wrist to the base of the middle finger (section 4.1).

    Those two points do not move when the fingers bend, so the scale stays
    put while the hand pinches.
    """
    return distance(wrist, middle_base)


def pinch_distance_hs(thumb_tip: Point, index_tip: Point, scale: float) -> float | None:
    """Thumb tip to index tip, in hand-scale units.

    `None` for a hand of zero size, which has no scale to measure against.
    Only made-up data can produce one, but a division is never left unguarded.
    """
    if scale == 0:
        return None
    return distance(thumb_tip, index_tip) / scale


def pinch_point(thumb_tip: Point, index_tip: Point) -> Point:
    """Halfway between the two fingertips: where a pinch is "held" (4.2)."""
    return ((thumb_tip[0] + index_tip[0]) / 2, (thumb_tip[1] + index_tip[1]) / 2)


def next_pinch(was_pinching: bool, distance_hs: float | None) -> bool:
    """Whether a hand is pinching now, given whether it was a frame ago.

    A pinch starts only when the fingertips close to below the start
    threshold, and ends only when they open past the wider end threshold.
    Between the two, the hand keeps whatever state it had.
    """
    if distance_hs is None:
        return False
    if was_pinching:
        return distance_hs <= config.PINCH_END_HS
    return distance_hs < config.PINCH_START_HS


def _smoothing_factor(cutoff_hz: float, dt_s: float) -> float:
    """How far a low-pass filter moves toward a new sample, 0 to 1.

    The standard first-order filter at this cutoff, sampled `dt_s` apart.
    """
    time_constant = 1.0 / (2.0 * math.pi * cutoff_hz)
    return 1.0 / (1.0 + time_constant / dt_s)


class OneEuroFilter:
    """Smooths one number that changes over time (Casiez, Roussel, Vogel, 2012).

    A low-pass filter whose cutoff rises with speed: at rest it sits at
    `min_cutoff_hz` and removes jitter, and every unit of speed adds `beta` to
    it so fast movement is followed with little lag. The speed itself is
    filtered at `derivative_cutoff_hz` so one noisy sample cannot open the
    filter up. Follows the authors' reference implementation, including that
    the first sample passes through unchanged with a speed of zero.
    """

    def __init__(
        self, min_cutoff_hz: float, beta: float, derivative_cutoff_hz: float
    ) -> None:
        self._min_cutoff_hz = min_cutoff_hz
        self._beta = beta
        self._derivative_cutoff_hz = derivative_cutoff_hz
        self._value: float | None = None
        self._speed = 0.0
        self._time_s = 0.0

    def __call__(self, value: float, time_s: float) -> float:
        """Filter `value`, sampled at `time_s` seconds. Times must increase."""
        if self._value is None:
            self._value = value
            self._time_s = time_s
            return value

        dt_s = time_s - self._time_s
        self._time_s = time_s
        speed = (value - self._value) / dt_s
        self._speed += _smoothing_factor(self._derivative_cutoff_hz, dt_s) * (
            speed - self._speed
        )
        cutoff_hz = self._min_cutoff_hz + self._beta * abs(self._speed)
        self._value += _smoothing_factor(cutoff_hz, dt_s) * (value - self._value)
        return self._value


def _landmark_filter() -> OneEuroFilter:
    return OneEuroFilter(
        config.SMOOTHING_MIN_CUTOFF_HZ,
        config.SMOOTHING_BETA,
        config.SMOOTHING_DERIVATIVE_CUTOFF_HZ,
    )


@dataclass(frozen=True)
class TrackedHand:
    """One hand's measurements in one frame. Points are in picture-height units.

    `pinch_distance_hs` is `None` only for a hand of zero size.
    """

    hand_id: int
    gesture: str
    gesture_score: float
    wrist: Point
    scale: float
    pinch_distance_hs: float | None
    pinching: bool
    pinch_point: Point


class _HandMemory:
    """What is remembered about one hand between frames."""

    def __init__(self, hand_id: int) -> None:
        self.hand_id = hand_id
        # Two filters - x and y - for each landmark used.
        self.filters = {
            index: (_landmark_filter(), _landmark_filter())
            for index in _USED_LANDMARKS
        }
        self.wrist: Point = (0.0, 0.0)
        self.pinching = False

    def measure(self, hand: Hand, aspect: float, time_s: float) -> TrackedHand:
        points = {}
        for index, (filter_x, filter_y) in self.filters.items():
            x, y = to_picture_units(hand.landmarks[index], aspect)
            points[index] = (filter_x(x, time_s), filter_y(y, time_s))

        scale = hand_scale(points[WRIST], points[MIDDLE_BASE])
        distance_hs = pinch_distance_hs(points[THUMB_TIP], points[INDEX_TIP], scale)
        self.wrist = points[WRIST]
        self.pinching = next_pinch(self.pinching, distance_hs)
        return TrackedHand(
            hand_id=self.hand_id,
            gesture=hand.gesture,
            gesture_score=hand.gesture_score,
            wrist=points[WRIST],
            scale=scale,
            pinch_distance_hs=distance_hs,
            pinching=self.pinching,
            pinch_point=pinch_point(points[THUMB_TIP], points[INDEX_TIP]),
        )


class HandMetrics:
    """Measures every hand in each frame, remembering each hand between frames.

    Call `update` once per frame, in order.
    """

    def __init__(self) -> None:
        self._memories: list[_HandMemory] = []
        self._next_id = 0

    def update(self, frame: HandFrame) -> tuple[TrackedHand, ...]:
        wrists = [
            to_picture_units(hand.landmarks[WRIST], frame.aspect)
            for hand in frame.hands
        ]
        matched = _match(wrists, [memory.wrist for memory in self._memories])

        memories = []
        for new_index in range(len(frame.hands)):
            old_index = matched.get(new_index)
            if old_index is None:
                memories.append(_HandMemory(self._next_id))
                self._next_id += 1
            else:
                memories.append(self._memories[old_index])
        # Hands that were not matched are gone, and so is what was known
        # about them.
        self._memories = memories

        time_s = frame.timestamp_ms / 1000.0
        return tuple(
            memory.measure(hand, frame.aspect, time_s)
            for memory, hand in zip(memories, frame.hands)
        )


def _match(new: list[Point], old: list[Point]) -> dict[int, int]:
    """Pair new wrists with old ones so the total distance moved is smallest.

    Returns {new index: old index}. As many pairs are made as the shorter list
    allows; the rest are new hands, or hands that left. At most two hands are
    tracked, so trying every pairing costs nothing.
    """
    size = max(len(new), len(old))
    best: dict[int, int] = {}
    best_cost = math.inf
    for order in permutations(range(size)):
        pairs = {
            new_index: old_index
            for new_index, old_index in enumerate(order)
            if new_index < len(new) and old_index < len(old)
        }
        cost = sum(distance(new[n], old[o]) for n, o in pairs.items())
        if cost < best_cost:
            best, best_cost = pairs, cost
    return best

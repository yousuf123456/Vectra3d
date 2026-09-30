"""What the gesture state machine asks for.

The state machine never changes a vector (`architecture.md` section 2). It
says what the hands are doing - "a two-hand create began here", "the steering
hand is now there", "commit", "cancel" - and the app turns that into the same
actions the panel uses.

Intents carry hand geometry, not vector maths. Points are in picture-height
units (see `hand_metrics`), and `scale` is the hand scale to measure them
against. Working out a magnitude, which hand is the head, or how far a
steer turns belongs to the steps that build each gesture (G5.3-G5.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vectra3d.gestures.hand_metrics import Point


class TwoHandKind(Enum):
    """Which two-hand gesture began: decided by how far apart the hands were."""

    CREATE = "create"
    RESIZE = "resize"


@dataclass(frozen=True)
class BeginSteer:
    """One hand is steering. `anchor` is its pinch point when the pinch began."""

    hand_id: int
    anchor: Point
    scale: float


@dataclass(frozen=True)
class UpdateSteer:
    """Where the steering hand's pinch point is now."""

    pinch_point: Point
    scale: float


@dataclass(frozen=True)
class BeginTwoHand:
    """Both hands are pinching: a create or a resize began.

    `hand_ids` and `start_points` are in the same order; `scale` is the two
    hands' average scale at that moment.
    """

    kind: TwoHandKind
    hand_ids: tuple[int, int]
    start_points: tuple[Point, Point]
    scale: float


@dataclass(frozen=True)
class UpdateTwoHand:
    """Where the two pinch points are now, in the order `BeginTwoHand` gave."""

    points: tuple[Point, Point]
    scale: float


@dataclass(frozen=True)
class Commit:
    """The gesture ended normally: keep what it did, as one undo step."""


@dataclass(frozen=True)
class Cancel:
    """An open palm cancelled the gesture: put everything back as it was."""


@dataclass(frozen=True)
class HoldTriggered:
    """A hold gesture was held long enough. `gesture` is MediaPipe's label."""

    gesture: str


Intent = (
    BeginSteer
    | UpdateSteer
    | BeginTwoHand
    | UpdateTwoHand
    | Commit
    | Cancel
    | HoldTriggered
)

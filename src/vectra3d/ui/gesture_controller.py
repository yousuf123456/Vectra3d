"""Turns the gesture state machine's intents into changes to the vectors.

`architecture.md` section 2: the gesture engine outputs intents and never
changes a vector; the app turns them into the same actions the panel uses.
This is that step. It holds what a gesture in progress needs to remember -
which vector it is moving, and where the hands began - and nothing else.

No Qt here, so it is tested by feeding it intents. The window hands it the
camera's direction and up each frame, since which way is "right" depends on
how the student has turned the view (`interaction-spec.md` section 6.1) -
for creating, and for which way a steer grabbed on the z axis leaves it.

Built so far: creating (G5.3), resizing (G5.4), steering by grab and drag
with snapping on release (G5.5 and G5.6, redone 2026-09-29), gesture
settings (G5.7) and the hold gestures (G5.8).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from vectra3d.core.formatting import format_number
from vectra3d.core.vector_math import magnitude
from vectra3d.gestures.hand_metrics import Point as PicturePoint
from vectra3d.gestures.hand_to_vector import (
    Heading,
    Meridian,
    Triple,
    at_pole,
    create_components,
    drag_meridian,
    hand_movement,
    heading_components,
    heading_of,
    is_long_enough,
    leave_pole,
    meridian_of,
    resize_components,
    screen_axes,
    snap_near,
    snapped,
)
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
from vectra3d.gestures.state_machine import POINTING_UP, THUMB_UP, VICTORY
from vectra3d.state import actions
from vectra3d.state.models import ORIGIN, Vector
from vectra3d.state.store import VectorStore
from vectra3d.ui.action_panel import LIMIT_TEXT

# Why a resize or a steer did nothing (`interaction-spec.md` sections 5, 6.3
# and 6.4). The locked wording is the spec's own.
NO_VECTOR_TEXT = "Create a vector first."
LOCKED_TEXT = "Vector {name} is locked."
NO_DIRECTION_TEXT = "Vector {name} has no direction to {verb}."
# Why a hold gesture did nothing (section 7).
ALL_LOCKED_TEXT = "All vectors are locked."
# What letting go would snap the steered vector to (section 6.5), shown
# while it is within reach. It keeps the word "Steering", which it takes
# the place of in the strip.
RELEASE_TEXT = "Steering: release to snap to {target}"


class _Kind(Enum):
    CREATE = "create"
    RESIZE = "resize"
    STEER = "steer"


@dataclass(frozen=True)
class Grab:
    """What the camera preview draws while steering (section 10).

    `anchor` is where the pinch began and `point` where it is now, both in
    picture-height units.
    """

    anchor: PicturePoint
    point: PicturePoint


class GestureController:
    """Applies one frame's intents to the store."""

    def __init__(self, store: VectorStore) -> None:
        self._store = store
        # The gesture moving a vector, and which vector.
        self._kind: _Kind | None = None
        self._moving: str | None = None
        # Create and resize: the intent that began them. Resize and steer:
        # the vector as it was when they began.
        self._begin: BeginTwoHand | None = None
        self._original: Vector | None = None
        # Steer: where the pinch began and is now, the angles the hand has
        # dragged the vector to, and where that is on its vertical circle
        # (None while it is still on the z axis it was grabbed on) (6.4).
        self._grab: Grab | None = None
        self._heading: Heading | None = None
        self._meridian: Meridian | None = None
        # The vector a release has just snapped, until the window asks.
        self._snapped_name: str | None = None
        # Why the last gesture did nothing, kept until the next one begins.
        self._notice: str | None = None

    @property
    def message(self) -> str | None:
        """What the camera preview should say instead of the gesture's name.

        Why the last gesture did nothing, if it did nothing; otherwise, while
        steering, what letting go would snap the vector to.
        """
        if self._notice is not None:
            return self._notice
        if self._heading is not None and self._store.settings.snapping:
            snap = snap_near(self._heading)
            if snap is not None:
                return RELEASE_TEXT.format(target=snap.label)
        return None

    def take_snapped(self) -> str | None:
        """The vector a release has snapped since this was last asked, for
        the flash, or None.

        A release that snaps nothing - already exactly on the axis or plane,
        or out of reach of one - does not count.
        """
        name, self._snapped_name = self._snapped_name, None
        return name

    @property
    def live_name(self) -> str | None:
        """The vector a hand is moving right now, or None."""
        return self._moving

    @property
    def grab(self) -> Grab | None:
        """Where the steering pinch began and is now, or None."""
        return self._grab

    def labels(self) -> dict[str, str]:
        """What to write at a vector's head instead of its letter.

        While a vector is being created or resized its label shows its live
        magnitude, "|A| = 4.20" (`interaction-spec.md` section 10). Steering
        keeps the letter: its numbers are the angles, which the arcs show.
        """
        if self._kind not in (_Kind.CREATE, _Kind.RESIZE):
            return {}
        vector = self._store.get(self._moving)
        if vector is None:
            return {}
        size = format_number(magnitude(vector.components))
        return {vector.name: f"|{vector.name}| = {size}"}

    def apply(
        self, intents: Iterable[Intent], camera_direction: Triple, camera_up: Triple
    ) -> None:
        for intent in intents:
            if isinstance(intent, BeginTwoHand):
                self._notice = None
                if intent.kind == TwoHandKind.CREATE:
                    self._begin_create(intent)
                else:
                    self._begin_on_active(_Kind.RESIZE, "resize", begin=intent)
            elif isinstance(intent, BeginSteer):
                self._notice = None
                if self._begin_on_active(_Kind.STEER, "steer"):
                    self._begin_steer(intent.anchor)
            elif isinstance(intent, UpdateTwoHand):
                self._update_two_hand(intent, camera_direction, camera_up)
            elif isinstance(intent, UpdateSteer):
                self._update_steer(intent, camera_direction, camera_up)
            elif isinstance(intent, Commit):
                self._commit()
            elif isinstance(intent, Cancel):
                self._cancel()
            elif isinstance(intent, HoldTriggered):
                self._notice = None
                self._hold(intent.gesture)

    def _hold(self, gesture: str) -> None:
        """Do what a held hand shape asks for (section 7).

        `Pointing_Up` makes the next unlocked vector active; `Thumb_Up`
        locks or unlocks the active vector; `Victory` shows or hides its
        components. The last two work on a locked vector: locking is how
        one is unlocked, and components change nothing about it - the panel
        allows both the same way. With no vectors nothing happens, and the
        student is told why.
        """
        active = self._store.active
        if active is None:
            self._notice = NO_VECTOR_TEXT
        elif gesture == POINTING_UP:
            if actions.activate_next(self._store) is None:
                self._notice = ALL_LOCKED_TEXT
        elif gesture == THUMB_UP:
            actions.toggle_locked(self._store, active.name)
        elif gesture == VICTORY:
            actions.toggle_components(self._store, active.name)

    def _begin_create(self, intent: BeginTwoHand) -> None:
        """Start a new vector at zero length (6.2 step 1).

        It is a real vector from the start, with its letter and colour, so
        the 3D view and the info panel follow it live. If ten already exist
        nothing is drawn and the student is told why (6.2 step 5).
        """
        actions.begin_gesture(self._store)
        vector = actions.create_vector(self._store, ORIGIN)
        if vector is None:
            actions.cancel_gesture(self._store)
            self._notice = LIMIT_TEXT
            return
        self._kind, self._moving, self._begin = _Kind.CREATE, vector.name, intent

    def _begin_on_active(
        self, kind: _Kind, verb: str, begin: BeginTwoHand | None = None
    ) -> bool:
        """Start resizing or steering the active vector (6.3, 6.4).

        Refused, with the reason in the camera strip, when there is nothing
        sensible to act on: no vector at all, a locked one (section 5), or
        the zero vector, which has no direction to keep or turn. A refusal
        changes nothing and records nothing. Returns whether it began.
        """
        vector = self._store.active
        if vector is None:
            self._notice = NO_VECTOR_TEXT
            return False
        if vector.locked:
            self._notice = LOCKED_TEXT.format(name=vector.name)
            return False
        if magnitude(vector.components) == 0.0:
            self._notice = NO_DIRECTION_TEXT.format(name=vector.name, verb=verb)
            return False
        actions.begin_gesture(self._store)
        self._kind, self._moving = kind, vector.name
        self._begin, self._original = begin, vector
        return True

    def _update_two_hand(
        self, intent: UpdateTwoHand, camera_direction: Triple, camera_up: Triple
    ) -> None:
        if self._moving is None or self._begin is None:
            return
        if self._kind == _Kind.CREATE:
            axes = screen_axes(camera_direction, camera_up)
            if axes is None:
                return
            components = create_components(
                self._begin.start_points,
                self._begin.scale,
                intent.points,
                intent.scale,
                axes,
                self._store.settings.sensitivity,
            )
        else:
            components = resize_components(
                self._original.components,
                self._begin.start_points,
                self._begin.scale,
                intent.points,
                intent.scale,
                self._store.settings.sensitivity,
            )
        if components is not None:
            actions.edit_vector(self._store, self._moving, components)


    def _begin_steer(self, anchor: PicturePoint) -> None:
        """Take the vector's angles (6.4).

        Movement is counted from where the pinch began, so any made during
        the two-hand window turns the vector on the first update. A vector
        grabbed exactly on the z axis has no vertical circle yet: the first
        movement picks one (`leave_pole`).
        """
        self._grab = Grab(anchor, anchor)
        self._heading = heading_of(self._original.components)
        self._meridian = None if at_pole(self._heading) else meridian_of(self._heading)

    def _update_steer(
        self, intent: UpdateSteer, camera_direction: Triple, camera_up: Triple
    ) -> None:
        """Turn the vector by as much as the hand moved since the last frame.

        A still hand changes nothing, so it costs no redraw. Up and down turn
        it round its vertical circle with no stop, over the top or under the
        bottom, and sideways always turns it the same way round z (6.4).
        Nothing snaps here: that waits for the release (6.5).
        """
        if self._kind != _Kind.STEER or self._grab is None:
            return
        movement = hand_movement(self._grab.point, intent.pinch_point, intent.scale)
        self._grab = Grab(self._grab.anchor, intent.pinch_point)
        axes = screen_axes(camera_direction, camera_up)
        vector = self._store.get(self._moving)
        if movement is None or axes is None or vector is None:
            return
        if self._meridian is None:
            self._heading = leave_pole(self._heading, movement, axes)
            if at_pole(self._heading):
                return
            self._meridian = meridian_of(self._heading)
        else:
            self._meridian = drag_meridian(self._meridian, movement)
            self._heading = self._meridian.heading
        shown = heading_components(self._heading, magnitude(self._original.components))
        if shown != vector.components:
            actions.edit_vector(self._store, self._moving, shown)

    def _landing(self) -> tuple[float, float, float] | None:
        """Where releasing the steer snaps the vector to, or None (6.5).

        None with snapping off, out of reach of every axis and plane, or
        already exactly on the one in reach, where snapping moves nothing.
        """
        if self._kind != _Kind.STEER or not self._store.settings.snapping:
            return None
        landed = snapped(self._heading, snap_near(self._heading))
        if landed == self._heading:
            return None
        return heading_components(landed, magnitude(self._original.components))

    def _commit(self) -> None:
        """Keep what the gesture did, as one undo step.

        A vector being created is dropped instead if it is too short to mean
        anything (6.2 step 4). A resized or steered one never is: neither can
        leave it shorter than the minimum magnitude. A steered one is snapped
        first, if it is within reach of an axis or plane, so the snap is part
        of the same undo step (6.5).

        The gesture is forgotten *before* the store is told, so the redraw
        that follows shows the vector's letter rather than its magnitude.
        """
        kind, name, landing = self._kind, self._moving, self._landing()
        self._forget()
        if name is None:
            return
        vector = self._store.get(name)
        if kind == _Kind.CREATE and (
            vector is None or not is_long_enough(vector.components)
        ):
            actions.cancel_gesture(self._store)
            return
        if landing is not None and vector is not None:
            actions.edit_vector(self._store, name, landing)
            self._snapped_name = name
        actions.commit_gesture(self._store)

    def _cancel(self) -> None:
        """Put the vector back exactly as it was, recording nothing (section 5).

        Only steering can be cancelled; the state machine never cancels a
        create or a resize. A cancelled steer does not snap.
        """
        name = self._moving
        self._forget()
        if name is not None:
            actions.cancel_gesture(self._store)

    def _forget(self) -> None:
        self._kind = self._moving = self._begin = self._original = None
        self._grab = self._heading = self._meridian = None

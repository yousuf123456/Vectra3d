"""Turns the gesture state machine's intents into changes to the vectors.

`architecture.md` section 2: the gesture engine outputs intents and never
changes a vector; the app turns them into the same actions the panel uses.
This is that step. It holds what a gesture in progress needs to remember -
which vector it is moving, and where the hands began - and nothing else.

No Qt here, so it is tested by feeding it intents. The window hands it the
camera's direction and up each frame, since which way is "right" depends on
how the student has turned the view (`interaction-spec.md` section 6.1), and
the frame's timestamp, since steering turns the vector at a rate per second.

Built so far: creating (G5.3), resizing (G5.4), steering (G5.5) and snapping
while steering (G5.6). The hold gestures arrive in G5.8; until then their
intents are ignored.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum

from vectra3d.core.formatting import format_number
from vectra3d.core.vector_math import magnitude
from vectra3d.gestures.hand_metrics import Point as PicturePoint
from vectra3d.gestures.hand_to_vector import (
    SnapTarget,
    Triple,
    angle_from,
    create_components,
    deflection,
    exact_target,
    is_long_enough,
    resize_components,
    screen_axes,
    snap_target,
    snapped_components,
    steer_components,
)
from vectra3d.gestures.intents import (
    BeginSteer,
    BeginTwoHand,
    Cancel,
    Commit,
    Intent,
    TwoHandKind,
    UpdateSteer,
    UpdateTwoHand,
)
from vectra3d.state import actions
from vectra3d.state.models import ORIGIN, Vector
from vectra3d.state.store import VectorStore
from vectra3d.ui.action_panel import LIMIT_TEXT

# Why a resize or a steer did nothing (`interaction-spec.md` sections 5, 6.3
# and 6.4). The locked wording is the spec's own.
NO_VECTOR_TEXT = "Create a vector first."
LOCKED_TEXT = "Vector {name} is locked."
NO_DIRECTION_TEXT = "Vector {name} has no direction to {verb}."
# What a steered vector is snapped to (section 6.5), shown while it holds.
# It keeps the word "Steering", which it takes the place of in the strip.
SNAPPED_TEXT = "Steering, snapped to {target}"


class _Kind(Enum):
    CREATE = "create"
    RESIZE = "resize"
    STEER = "steer"


@dataclass(frozen=True)
class Joystick:
    """What the camera preview draws while steering (section 10).

    Points are in picture-height units; `scale` is the hand scale at the
    anchor, which sets the size of the dead-zone ring.
    """

    anchor: PicturePoint
    point: PicturePoint
    scale: float


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
        # Steer: the joystick, and when it was last applied.
        self._joystick: Joystick | None = None
        self._last_ms: int | None = None
        # Steer: the direction the joystick has turned the vector to, before
        # snapping, and what it is snapped to (6.5).
        self._steered: Triple | None = None
        self._snap: SnapTarget | None = None
        self._snap_engaged = False
        # Why the last gesture did nothing, kept until the next one begins.
        self._notice: str | None = None

    @property
    def message(self) -> str | None:
        """What the camera preview should say instead of the gesture's name.

        Why the last gesture did nothing, if it did nothing; otherwise, while
        steering, what the vector is snapped to.
        """
        if self._notice is not None:
            return self._notice
        if self._snap is not None:
            return SNAPPED_TEXT.format(target=self._snap.label)
        return None

    def take_snap_engaged(self) -> bool:
        """Whether a snap engaged since this was last asked, for the flash.

        A vector already on an axis or plane when steering begins does not
        count: nothing arrived there.
        """
        engaged, self._snap_engaged = self._snap_engaged, False
        return engaged

    @property
    def live_name(self) -> str | None:
        """The vector a hand is moving right now, or None."""
        return self._moving

    @property
    def joystick(self) -> Joystick | None:
        """The joystick while steering, or None."""
        return self._joystick

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
        self,
        intents: Iterable[Intent],
        camera_direction: Triple,
        camera_up: Triple,
        now_ms: int,
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
                    self._joystick = Joystick(intent.anchor, intent.anchor, intent.scale)
                    self._last_ms = now_ms
                    self._steered = self._original.components
                    self._snap = (
                        exact_target(self._steered)
                        if self._store.settings.snapping
                        else None
                    )
            elif isinstance(intent, UpdateTwoHand):
                self._update_two_hand(intent, camera_direction, camera_up)
            elif isinstance(intent, UpdateSteer):
                self._update_steer(intent, camera_direction, camera_up, now_ms)
            elif isinstance(intent, Commit):
                self._commit()
            elif isinstance(intent, Cancel):
                self._cancel()

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

    def _update_steer(
        self,
        intent: UpdateSteer,
        camera_direction: Triple,
        camera_up: Triple,
        now_ms: int,
    ) -> None:
        """Turn the vector for the time since the last steering frame (6.4).

        Timed from the frames' own timestamps, so the vector turns at the
        same rate whatever the frame rate. Nothing is changed while the
        joystick sits in its dead zone, or while a snap holds the vector
        where it is, so a still hand costs no redraw.

        The joystick turns the steered direction; the store is given that
        direction snapped (6.5). See `hand_to_vector` for why the two differ.
        """
        if self._kind != _Kind.STEER or self._joystick is None:
            return
        self._joystick = Joystick(
            self._joystick.anchor, intent.pinch_point, self._joystick.scale
        )
        seconds = (now_ms - self._last_ms) / 1000.0
        self._last_ms = now_ms

        push = deflection(self._joystick.anchor, intent.pinch_point, self._joystick.scale)
        axes = screen_axes(camera_direction, camera_up)
        vector = self._store.get(self._moving)
        if push is None or axes is None or vector is None:
            return
        length = magnitude(self._original.components)
        # Snapping can be switched off mid-steer (F-20): the vector then goes
        # to wherever the hand has steered it, on this frame.
        if not self._store.settings.snapping:
            self._snap = None
        # Snapped, the joystick turns it within the plane or planes it lies in.
        locks = self._snap.locks if self._snap is not None else ()
        self._steered = steer_components(
            self._steered, length, push, seconds, axes, locks
        )

        target = (
            snap_target(self._steered, self._snap)
            if self._store.settings.snapping
            else None
        )
        # A snap engages when the vector jumps onto something new. Leaving
        # an axis along a plane it already lies in is a change of target
        # with no jump, and flashing then would announce nothing visible.
        shown = snapped_components(self._steered, length, target)
        if target is not None and target != self._snap:
            # Leaving an axis along one of its planes is not arriving
            # anywhere, even if the plane takes up a little drift.
            leaving = (
                self._snap is not None
                and not self._snap.is_plane
                and target.is_plane
                and target.index != self._snap.index
            )
            if not leaving and angle_from(self._steered, target) > 0.0:
                self._snap_engaged = True
            # From here the steering starts again from where the vector is
            # shown, so a drift the snap absorbed on the way in does not
            # carry into the next move. Only on arriving: reset every frame,
            # the steering could never get far enough away to let go.
            self._steered = shown
        self._snap = target
        if shown != vector.components:
            actions.edit_vector(self._store, self._moving, shown)

    def _commit(self) -> None:
        """Keep what the gesture did, as one undo step.

        A vector being created is dropped instead if it is too short to mean
        anything (6.2 step 4). A resized or steered one never is: neither can
        leave it shorter than the minimum magnitude.

        The gesture is forgotten *before* the store is told, so the redraw
        that follows shows the vector's letter rather than its magnitude.
        """
        kind, name = self._kind, self._moving
        self._forget()
        if name is None:
            return
        vector = self._store.get(name)
        if kind == _Kind.CREATE and (
            vector is None or not is_long_enough(vector.components)
        ):
            actions.cancel_gesture(self._store)
        else:
            actions.commit_gesture(self._store)

    def _cancel(self) -> None:
        """Put the vector back exactly as it was, recording nothing (section 5).

        Only steering can be cancelled; the state machine never cancels a
        create or a resize.
        """
        name = self._moving
        self._forget()
        if name is not None:
            actions.cancel_gesture(self._store)

    def _forget(self) -> None:
        self._kind = self._moving = self._begin = self._original = None
        self._joystick = self._last_ms = None
        self._steered = self._snap = None
        self._snap_engaged = False

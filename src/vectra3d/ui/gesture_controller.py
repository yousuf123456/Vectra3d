"""Turns the gesture state machine's intents into changes to the vectors.

`architecture.md` section 2: the gesture engine outputs intents and never
changes a vector; the app turns them into the same actions the panel uses.
This is that step. It holds what a gesture in progress needs to remember -
which vector it is drawing, and where the hands began - and nothing else.

No Qt here, so it is tested by feeding it intents. The window hands it the
camera's direction and up each frame, since which way is "right" depends on
how the student has turned the view (`interaction-spec.md` section 6.1).

Built so far: creating (G5.3). Resizing, steering and the hold gestures
arrive in G5.4, G5.5 and G5.8; until then their intents are ignored.
"""

from __future__ import annotations

from collections.abc import Iterable

from vectra3d import config
from vectra3d.core.formatting import format_number
from vectra3d.core.vector_math import magnitude
from vectra3d.gestures.hand_to_vector import (
    Triple,
    create_components,
    is_long_enough,
    screen_axes,
)
from vectra3d.gestures.intents import (
    BeginSteer,
    BeginTwoHand,
    Commit,
    Intent,
    TwoHandKind,
    UpdateTwoHand,
)
from vectra3d.state import actions
from vectra3d.state.models import ORIGIN
from vectra3d.state.store import VectorStore
from vectra3d.ui.action_panel import LIMIT_TEXT


class GestureController:
    """Applies one frame's intents to the store."""

    def __init__(self, store: VectorStore) -> None:
        self._store = store
        # The vector being created, and the intent that began it.
        self._creating: str | None = None
        self._begin: BeginTwoHand | None = None
        # Something the student should be told in the camera preview, kept
        # until the next gesture begins.
        self.message: str | None = None

    @property
    def live_name(self) -> str | None:
        """The vector a hand is moving right now, or None."""
        return self._creating

    def labels(self) -> dict[str, str]:
        """What to write at a vector's head instead of its letter.

        While a vector is being created its label shows its live magnitude,
        "|A| = 4.20" (`interaction-spec.md` section 10).
        """
        vector = self._store.get(self._creating) if self._creating else None
        if vector is None:
            return {}
        size = format_number(magnitude(vector.components))
        return {vector.name: f"|{vector.name}| = {size}"}

    def apply(
        self, intents: Iterable[Intent], camera_direction: Triple, camera_up: Triple
    ) -> None:
        for intent in intents:
            if isinstance(intent, BeginTwoHand):
                self.message = None
                if intent.kind == TwoHandKind.CREATE:
                    self._begin_create(intent)
            elif isinstance(intent, BeginSteer):
                self.message = None
            elif isinstance(intent, UpdateTwoHand):
                self._update_create(intent, camera_direction, camera_up)
            elif isinstance(intent, Commit):
                self._commit_create()

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
            self.message = LIMIT_TEXT
            return
        self._creating = vector.name
        self._begin = intent

    def _update_create(
        self, intent: UpdateTwoHand, camera_direction: Triple, camera_up: Triple
    ) -> None:
        if self._creating is None or self._begin is None:
            return
        axes = screen_axes(camera_direction, camera_up)
        if axes is None:
            return
        components = create_components(
            self._begin.start_points,
            self._begin.scale,
            intent.points,
            intent.scale,
            axes,
            config.MAGNITUDE_SENSITIVITY_DEFAULT,
        )
        if components is not None:
            actions.edit_vector(self._store, self._creating, components)

    def _commit_create(self) -> None:
        """Keep the vector, unless it is too short to mean anything (6.2 step 4).

        The gesture is forgotten *before* the store is told, so the redraw
        that follows shows the vector's letter rather than its magnitude.
        """
        name, self._creating, self._begin = self._creating, None, None
        if name is None:
            return
        vector = self._store.get(name)
        if vector is None or not is_long_enough(vector.components):
            actions.cancel_gesture(self._store)
        else:
            actions.commit_gesture(self._store)

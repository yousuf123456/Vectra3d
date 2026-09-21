"""The 3D scene: axes, grid, origin, and how big the world currently is.

The scene draws the space the vectors live in. It owns no vector data; it is
told the vectors and draws to fit them.

**Scene extent** is the half-width of the world in scene units: the grid and
the axes run from -extent to +extent. It starts at 10 and follows the sequence
in `interaction-spec.md` section 3 (10, 20, 50, 100, 200, 500, 1000, ...),
growing when a vector no longer fits and shrinking back when it does. That is
separate from zooming, which the student does with the mouse and which never
changes the extent.

The constants below are scene layout rather than feel: how dense the grid is,
where the camera sits, how big the arrowheads are. They are not in `config.py`
because that file holds the values `interaction-spec.md` section 9 marks as
tunable after testing with real hands, and changing those is a decision that
has to be recorded. Changing the grid spacing is not.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

import numpy as np
import pyvista as pv

from vectra3d.state.models import Vector

# The smallest the world ever gets (`interaction-spec.md` section 3).
MIN_EXTENT = 10.0

# Grid lines and tick marks every extent/10; numbers every extent/5, so the
# numbers stay readable instead of crowding into each other.
DIVISIONS = 10
LABEL_EVERY = 2

# Axis colors, shared with the component vectors (`interaction-spec.md` 2.1).
AXIS_COLORS = {"x": "#CC0000", "y": "#00AA00", "z": "#0044CC"}
GRID_COLOR = "#CCCCCC"
ORIGIN_COLOR = "#444444"
LABEL_COLOR = "#333333"

# Sizes as fractions of the extent, so the scene looks the same at every size.
ARROW_LENGTH = 0.06
ARROW_RADIUS = 0.018
ORIGIN_RADIUS = 0.012
TICK_LENGTH = 0.012

AXIS_FONT_SIZE = 16
NUMBER_FONT_SIZE = 10

# Where the camera sits by default: raised, in front and to the right, so that
# x, y and z are all clearly visible (`interaction-spec.md` section 2.1).
CAMERA_DIRECTION = (1.0, -1.35, 0.75)
VIEW_UP = (0.0, 0.0, 1.0)

# How much of the world has to be on screen, in multiples of the extent.
#
# The furthest thing out is an axis letter, which sits a little past the tip
# of its axis: 1 + ARROW_LENGTH * 2.2, about 1.13 extents. The rest is margin
# so the letters are not jammed against the edge of the view.
#
# The camera distance is worked out from this and the lens angle rather than
# being a number of its own. It used to be a fixed 3.1 extents, which was too
# close for its own scene: the visible half-height there is 3.1 * tan(15) =
# 0.83 extents, so the axes were cut off before their tips, and the x and z
# letters were outside the picture entirely. It was only obvious once the
# preset views arrived, because looking straight down an axis foreshortens
# nothing and the letters have nowhere to hide.
VISIBLE_RADIUS = 1.30

# How far the numbers sit off their axis, as a fraction of the extent. The
# direction is decided per view in `place_labels`; this is only the distance.
LABEL_OFFSET = 0.045

# An axis within about 12 degrees of pointing straight at the camera is hidden
# along with its numbers: it is a point on screen, so there is nothing to read
# along it, and every one of its numbers would land on the origin at once.
AXIS_HEAD_ON_LIMIT = 0.978  # cos(12 degrees)

# Below this, an axis counts as running up and down the screen, where "push
# the numbers downwards" is meaningless and they go to the left instead.
UPRIGHT_AXIS_LIMIT = 0.2

# The named viewpoints in the toolbar: which way the camera sits from the
# origin, and which way is up on screen once it is there.
#
# Looking down an axis, "up" is z, the way the student is used to seeing it.
# Looking down z itself that is meaningless, since z points at them, so the
# top of the screen becomes +y and the view reads like a map of the XY plane.
VIEWPOINTS: dict[str, tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    "Front": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "Right": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "Top": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
}


def extent_steps() -> Iterable[float]:
    """The allowed scene extents, smallest first: 10, 20, 50, 100, 200, ...

    The 1, 2, 5 pattern repeats through every power of ten, so the grid always
    divides into a round number of squares and the numbers on the axes stay
    easy to read.
    """
    decade = MIN_EXTENT
    while True:
        for multiplier in (1, 2, 5):
            yield multiplier * decade
        decade *= 10


def extent_for(max_abs: float) -> float:
    """Return the smallest extent that fits a value this far from the origin.

    Never smaller than 10. A value exactly on the boundary fits, so a vector
    reaching exactly 10 does not make the world grow.

    A value that is not finite is refused rather than searched for. There is
    no extent that fits infinity, and every comparison against a nan is
    false, so looking for one would walk the sequence forever and freeze the
    window with nothing to show for it. Typed input is already turned away
    in the panel; this is the backstop for values that arrive by any other
    route, and it fails loudly instead of hanging.
    """
    if not math.isfinite(max_abs):
        raise ValueError(f"the scene cannot be sized to fit {max_abs}")

    for step in extent_steps():
        if step >= max_abs:
            return step
    raise AssertionError("extent_steps never runs out")  # pragma: no cover


def extent_for_vectors(vectors: Sequence[Vector]) -> float:
    """Return the extent that fits every component of every vector."""
    values = [abs(c) for vector in vectors for c in vector.components]
    return extent_for(max(values, default=0.0))


def _segments(pairs: Sequence[tuple[Sequence[float], Sequence[float]]]) -> pv.PolyData:
    """Build one mesh of separate line segments, so they need only one actor."""
    points = np.array([point for pair in pairs for point in pair], dtype=float)
    lines = np.column_stack(
        [
            np.full(len(pairs), 2),
            np.arange(0, 2 * len(pairs), 2),
            np.arange(1, 2 * len(pairs), 2),
        ]
    ).ravel()
    return pv.PolyData(points, lines=lines)


def _format_tick(value: float) -> str:
    """Whole numbers without a trailing '.0', which is noise on an axis."""
    return f"{value:g}"


def label_offset_direction(
    axis: np.ndarray, view: np.ndarray, up: np.ndarray
) -> np.ndarray | None:
    """Which way to push an axis's numbers so they can be read on screen.

    `axis` is the axis direction, `view` the way the camera is looking, `up`
    the camera's up direction, all in world space. Returns a unit vector
    perpendicular to the axis and lying in the plane of the screen, or None
    if the axis points so nearly at the camera that it is a point on screen
    and its numbers should not be drawn at all.

    `cross(axis, view)` is perpendicular to both, which makes it "sideways
    from this axis, as the student sees it". The sign is then chosen so the
    numbers hang below their axis, as on a printed graph. An axis drawn
    up and down the screen has no below, so its numbers go to the left.
    """
    view = view / np.linalg.norm(view)
    if abs(float(np.dot(axis, view))) >= AXIS_HEAD_ON_LIMIT:
        return None

    sideways = np.cross(axis, view)
    length = float(np.linalg.norm(sideways))
    if length == 0.0:  # pragma: no cover - the head-on check already caught it
        return None
    sideways /= length

    downwards = float(np.dot(sideways, up))
    if abs(downwards) < UPRIGHT_AXIS_LIMIT:
        right = np.cross(view, up)
        if float(np.dot(sideways, right)) > 0.0:
            sideways = -sideways
    elif downwards > 0.0:
        sideways = -sideways
    return sideways


class Scene:
    """Draws the world the vectors live in, and resizes it to fit them.

    Everything here runs on the main thread; the tracker thread never calls in.
    """

    def __init__(self, plotter: pv.Plotter) -> None:
        self._plotter = plotter
        self._extent = MIN_EXTENT

        # Filled in by `_draw`, then arranged for the current view by
        # `place_labels`: the numbers with the point on the axis each belongs
        # to, the three axis letters, and where each axis is pushing its
        # numbers at the moment.
        self._numbers: list[tuple[int, np.ndarray, pv.Label]] = []
        self._letters: dict[int, pv.Label] = {}
        self._offsets: list[np.ndarray] = [np.zeros(3) for _ in range(3)]
        self._axis_visible: list[bool] = [True, True, True]

        self._draw()
        self.reset_view()

        # Keep the labels arranged while the student drags the view around.
        # The plotter has no interactor when rendering off screen, as the
        # tests and the screenshot scripts do.
        interactor = getattr(self._plotter, "iren", None)
        if interactor is not None:
            interactor.add_observer("InteractionEvent", self._on_camera_moved)

    def _on_camera_moved(self, *_args: object) -> None:
        """Rearrange the labels as the view turns. Called on every drag frame."""
        self.place_labels()

    @property
    def extent(self) -> float:
        return self._extent

    # --- Drawing ---

    def _draw(self) -> None:
        """Draw the grid, axes and origin at the current extent.

        Every actor is added with a `name`, which makes PyVista replace the
        one already there. Redrawing at a new extent therefore updates the
        scene in place instead of piling actors on top of each other.

        Nothing is rendered here. `add_mesh` renders by default, which drew a
        frame after each actor was replaced, with the grid already removed and
        not yet put back. Callers render once, after the camera has been moved
        to match, so the whole change lands in a single frame.
        """
        extent = self._extent
        self._draw_grid(extent)
        self._draw_axes(extent)
        self._draw_numbers(extent)
        self._plotter.add_mesh(
            pv.Sphere(radius=ORIGIN_RADIUS * extent, center=(0.0, 0.0, 0.0)),
            color=ORIGIN_COLOR,
            name="origin",
            render=False,
        )

    def _draw_grid(self, extent: float) -> None:
        """A flat grid on the XY plane, the floor the scene stands on.

        Built from plain line segments rather than a wireframe plane. The
        plane was the obvious way and was measured as the single most
        expensive thing in the scene: a wireframe draws all four edges of
        every one of its four hundred squares, which is each line over
        again. These are the forty-two lines actually wanted.
        """
        step = extent / DIVISIONS
        pairs = []
        for i in range(-DIVISIONS, DIVISIONS + 1):
            at = i * step
            pairs.append(((-extent, at, 0.0), (extent, at, 0.0)))
            pairs.append(((at, -extent, 0.0), (at, extent, 0.0)))

        self._plotter.add_mesh(
            _segments(pairs),
            color=GRID_COLOR,
            line_width=1,
            lighting=False,
            name="grid",
            render=False,
        )

    def _draw_axes(self, extent: float) -> None:
        """Each axis as a full line through the origin, with a head and a letter."""
        step = extent / DIVISIONS
        tick = TICK_LENGTH * extent

        for index, (label, color) in enumerate(AXIS_COLORS.items()):
            direction = np.zeros(3)
            direction[index] = 1.0
            tip = direction * extent

            self._plotter.add_mesh(
                pv.Line(-tip, tip),
                color=color,
                line_width=2,
                lighting=False,
                name=f"axis-{label}",
                render=False,
            )
            self._plotter.add_mesh(
                pv.Cone(
                    center=tip + direction * (ARROW_LENGTH * extent / 2),
                    direction=direction,
                    height=ARROW_LENGTH * extent,
                    radius=ARROW_RADIUS * extent,
                ),
                color=color,
                name=f"head-{label}",
                render=False,
            )

            # Tick marks, drawn across the axis in the two directions it does
            # not point, so they are visible from wherever the camera is.
            across = [np.roll(direction, 1), np.roll(direction, 2)]
            pairs = []
            for i in range(-DIVISIONS, DIVISIONS + 1):
                if i == 0:
                    continue
                at = direction * (i * step)
                for offset in across:
                    pairs.append((at - offset * tick, at + offset * tick))
            self._plotter.add_mesh(
                _segments(pairs),
                color=color,
                line_width=1,
                lighting=False,
                name=f"ticks-{label}",
                render=False,
            )

            self._letters[index] = self._label(
                label,
                tip + direction * (ARROW_LENGTH * 2.2 * extent),
                AXIS_FONT_SIZE,
                color,
                f"letter-{label}",
            )

    def _draw_numbers(self, extent: float) -> None:
        """The numbers along each axis, so magnitudes can be read off the scene.

        Placed on the axis itself here. Where they actually sit is decided by
        `place_labels`, which pushes them clear of the axis in whichever
        direction is clear *on screen* for the current view.
        """
        step = extent / DIVISIONS

        self._numbers = []
        for index in range(3):
            direction = np.zeros(3)
            direction[index] = 1.0
            for i in range(-DIVISIONS, DIVISIONS + 1, LABEL_EVERY):
                if i == 0:
                    continue
                label = self._label(
                    _format_tick(i * step),
                    direction * (i * step),
                    NUMBER_FONT_SIZE,
                    LABEL_COLOR,
                    f"number-{index}-{i}",
                )
                self._numbers.append((index, direction * (i * step), label))

    # --- Where the labels sit ---

    def place_labels(self) -> None:
        """Move every axis label to where it can be read from this viewpoint.

        The numbers used to be nudged off their axis in a fixed world
        direction - x numbers towards -y, y and z towards -x. Those
        directions suit the default view and no other. Turn the scene and
        they push the numbers onto the axis line, across a vector, or into
        each other; look straight down an axis and every number on it lands
        on the origin in a single unreadable smudge.

        So the direction is worked out per axis, per view. `cross(axis,
        view)` is perpendicular to the axis and lies in the plane of the
        screen, which is exactly the "sideways from this axis, as the student
        sees it" direction. Its sign is chosen to push the numbers down the
        screen, or, for an axis that is already near-vertical on screen and
        so has no meaningful "down", to the left.

        An axis pointing within a few degrees of the camera is hidden
        outright, numbers and letter both. There is nothing to read along an
        axis that is a single point on screen, and stacking twenty numbers on
        the origin is worse than showing none.
        """
        camera = self._plotter.camera
        view = np.array(camera.direction, dtype=float)
        up = np.array(camera.up, dtype=float)
        offset = LABEL_OFFSET * self._extent

        for index in range(3):
            axis = np.zeros(3)
            axis[index] = 1.0
            sideways = label_offset_direction(axis, view, up)

            visible = sideways is not None
            self._axis_visible[index] = visible
            letter = self._letters.get(index)
            if letter is not None:
                letter.SetVisibility(visible)
            if sideways is not None:
                self._offsets[index] = sideways * offset

        for index, base, label in self._numbers:
            label.SetVisibility(self._axis_visible[index])
            if self._axis_visible[index]:
                label.position = tuple(float(v) for v in base + self._offsets[index])

    def _label(
        self,
        text: str,
        position: np.ndarray,
        size: int,
        color: str,
        name: str,
    ) -> pv.Label:
        """Place one piece of text in the scene, facing the camera.

        `pv.Label` is a billboard: it turns to face the viewer and costs
        nothing to draw. `add_point_labels` was the obvious choice and was
        measured at less than half the frame rate, because it runs a
        collision pass to stop labels overlapping. The scene has few enough
        numbers that they do not collide anyway (see `library-docs.md`).
        """
        label = pv.Label(
            text=text,
            position=tuple(float(v) for v in position),
            size=size,
        )
        label.prop.color = color
        self._plotter.add_actor(label, name=name, reset_camera=False, render=False)
        return label

    # --- The camera ---

    def camera_distance(self) -> float:
        """How far back the camera has to sit for the whole world to fit.

        Read from the camera's own lens angle rather than assumed, so the
        framing stays right if that angle is ever changed. VTK's view angle
        is the vertical one, which is the tighter of the two on a window
        wider than it is tall, so fitting it fits the width as well.
        """
        half_angle = math.radians(self._plotter.camera.view_angle / 2.0)
        return VISIBLE_RADIUS * self._extent / math.tan(half_angle)

    def default_camera_position(self) -> list[tuple[float, float, float]]:
        """The default viewpoint for the current extent."""
        direction = np.array(CAMERA_DIRECTION, dtype=float)
        direction /= np.linalg.norm(direction)
        position = direction * self.camera_distance()
        return [tuple(float(v) for v in position), (0.0, 0.0, 0.0), VIEW_UP]

    def reset_view(self) -> None:
        """Put the camera back at the default angle (F-01)."""
        self._plotter.camera_position = self.default_camera_position()
        self.place_labels()
        self._plotter.render()

    def set_view(self, name: str) -> None:
        """Look at the scene from one of the named directions.

        The default angle shows all three axes at once, which is right for
        seeing a vector as a whole but poor for judging it: from an angle,
        a vector leaning towards x looks much like one leaning towards y.
        Looking straight down an axis removes that guesswork, because the
        axis pointing at the student collapses to a point and the other two
        are seen true.

        The camera is placed by hand rather than through PyVista's
        `view_xy` and friends, for two reasons. Those helpers frame the
        scene's bounds, so the framing would jump about as vectors are
        created and deleted; and they choose their own up direction, which
        for a z-up scene puts the top of the screen somewhere unexpected.
        Placing it keeps every view at the same distance, with z up wherever
        z is on screen, so switching views feels like walking around one
        fixed object.
        """
        direction, view_up = VIEWPOINTS[name]
        position = np.array(direction, dtype=float) * self.camera_distance()
        self._plotter.camera_position = [
            tuple(float(v) for v in position),
            (0.0, 0.0, 0.0),
            view_up,
        ]
        self.place_labels()
        self._plotter.render()

    # --- Resizing the world ---

    def update_for(self, vectors: Sequence[Vector]) -> None:
        """Grow or shrink the world so every vector fits.

        Called when the vectors change, which is exactly when
        `interaction-spec.md` section 3 allows rescaling: after a typed value
        is applied, a vector is deleted or cleared, an undo, or later a
        released gesture. Never while a vector is being moved by hand,
        because a gesture in progress does not change the store.
        """
        needed = extent_for_vectors(vectors)
        if needed != self._extent:
            self.set_extent(needed)

    def set_extent(self, extent: float) -> None:
        """Redraw at a new extent, moving the camera in the same frame.

        Everything in the scene is a fraction of the extent: the grid, the
        arrowheads, the origin dot, and how far away the camera sits. They
        have to change together. An earlier version redrew the geometry at
        once and slid the camera out over 300 ms to follow, which meant that
        for those 300 ms the world really was ten times too big with the
        camera far too close: the origin dot filled the view and the grid
        lines shot past the edges of the screen.

        Changing both in one frame is also what makes this look calm. The
        grid always has the same number of divisions and the camera distance
        is proportional, so the lines land in almost the same pixels. What
        changes on screen is the numbers on the axes, which is exactly the
        information the student needs.

        Only the camera's distance changes. The direction they are looking
        from is left alone, because swinging the view back to the default
        angle just because a vector grew would be its own kind of rude.
        """
        previous = self._extent
        self._extent = extent
        self._draw()

        position = np.array(self._plotter.camera.position, dtype=float)
        focal = np.array(self._plotter.camera.focal_point, dtype=float)
        moved = focal + (position - focal) * (extent / previous)
        self._plotter.camera.position = tuple(float(v) for v in moved)
        # `_draw` built a fresh set of numbers sitting on their axes, so they
        # have to be arranged again before the frame goes out.
        self.place_labels()
        self._plotter.render()

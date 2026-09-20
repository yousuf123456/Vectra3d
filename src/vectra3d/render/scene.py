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
CAMERA_DISTANCE = 3.1  # multiples of the extent
VIEW_UP = (0.0, 0.0, 1.0)


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
    """
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


class Scene:
    """Draws the world the vectors live in, and resizes it to fit them.

    Everything here runs on the main thread; the tracker thread never calls in.
    """

    def __init__(self, plotter: pv.Plotter) -> None:
        self._plotter = plotter
        self._extent = MIN_EXTENT

        self._draw()
        self.reset_view()

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

            self._label(
                label,
                tip + direction * (ARROW_LENGTH * 2.2 * extent),
                AXIS_FONT_SIZE,
                color,
                f"letter-{label}",
            )

    def _draw_numbers(self, extent: float) -> None:
        """The numbers along each axis, so magnitudes can be read off the scene."""
        step = extent / DIVISIONS
        offset = TICK_LENGTH * 3 * extent

        # Which way to nudge the numbers so they sit clear of their axis. The
        # x and y numbers move across the floor rather than under it, and the
        # z numbers move sideways.
        nudge = {0: (0.0, 1.0, 0.0), 1: (1.0, 0.0, 0.0), 2: (1.0, 0.0, 0.0)}

        for index in range(3):
            direction = np.zeros(3)
            direction[index] = 1.0
            away = np.array(nudge[index])
            for i in range(-DIVISIONS, DIVISIONS + 1, LABEL_EVERY):
                if i == 0:
                    continue
                self._label(
                    _format_tick(i * step),
                    direction * (i * step) - away * offset,
                    NUMBER_FONT_SIZE,
                    LABEL_COLOR,
                    f"number-{index}-{i}",
                )

    def _label(
        self,
        text: str,
        position: np.ndarray,
        size: int,
        color: str,
        name: str,
    ) -> None:
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

    # --- The camera ---

    def default_camera_position(self) -> list[tuple[float, float, float]]:
        """The default viewpoint for the current extent."""
        direction = np.array(CAMERA_DIRECTION, dtype=float)
        direction /= np.linalg.norm(direction)
        position = direction * (CAMERA_DISTANCE * self._extent)
        return [tuple(float(v) for v in position), (0.0, 0.0, 0.0), VIEW_UP]

    def reset_view(self) -> None:
        """Put the camera back at the default angle (F-01)."""
        self._plotter.camera_position = self.default_camera_position()
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
        self._plotter.render()

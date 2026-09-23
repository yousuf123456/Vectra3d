"""The main application window, with the 3D view embedded in it.

The 3D view is a PyVista `QtInteractor`, which is a Qt widget wrapping a VTK
render window. Embedding it means the 3D scene lives inside the same window as
the panels, rather than in a separate floating window (which is what PyVista's
BackgroundPlotter would give us).

The window subclasses `pyvistaqt.MainWindow` rather than Qt's own QMainWindow
purely for its `signal_close`, which fires as the window closes and is how the
plotter gets shut down in time. Without that, VTK can be left holding a render
window after Qt has gone, which shows up as a hang on exit.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from pyvistaqt import MainWindow, QtInteractor
from PySide6.QtWidgets import (
    QFrame,
    QLineEdit,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from vectra3d.render.animations import ComponentTransition, HeadToTail
from vectra3d.render.overlays import ComponentOverlays, ProjectionOverlays
from vectra3d.state import actions, naming
from vectra3d.render.result_actor import ResultActor
from vectra3d.render.scene import Scene
from vectra3d.render.vector_actor import VectorActors
from vectra3d.state.store import VectorStore
from vectra3d.ui import theme
from vectra3d.ui.action_panel import ActionPanel
from vectra3d.ui.info_panel import InfoPanel

WINDOW_TITLE = "Vectra3D"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
PANEL_WIDTH = 300

# Anti-aliasing settings, chosen by measuring on the integrated graphics this
# app targets (Intel HD Graphics 620) against a scene of thin lines, which is
# what the app mostly draws: axes, grid, and dashed projection lines.
#
# PyVista's default of 8x multisampling runs at 37 fps. Dropping to 2x and
# adding FXAA and line smoothing runs at 60 fps, the display's limit, and
# still keeps lines clean. 4x was the next step up in quality but cost a third
# of the frame rate (47 fps) for a difference that is hard to see.
#
# The frame rate matters beyond looks: F-02 requires hand tracking not to slow
# the 3D view, and MediaPipe will be competing for this same modest chip.
MULTI_SAMPLES = 2
LINE_SMOOTHING = True

# What each preset view button says it does, in the student's terms rather
# than in axis names alone.
VIEW_HINTS = {
    "Front": "Look along the y axis: x across, z up",
    "Right": "Look along the x axis: y across, z up",
    "Top": "Look down the z axis onto the XY plane",
}


class VectraMainWindow(MainWindow):
    """The application window: a toolbar and the 3D view.

    The window is given the store rather than creating one, because `app.py`
    is where the parts are wired together. The panels that will read and
    change the store arrive in G1.3 and G1.4.
    """

    def __init__(self, store: VectorStore) -> None:
        super().__init__()
        self._store = store

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        frame = QFrame(self)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = QtInteractor(
            frame,
            multi_samples=MULTI_SAMPLES,
            line_smoothing=LINE_SMOOTHING,
        )
        self.plotter.enable_anti_aliasing("fxaa")
        self.plotter.set_background(theme.SCENE_BACKGROUND)
        layout.addWidget(self.plotter.interactor)

        # The 3D view on the left, the panels on the right. A splitter lets
        # the student widen either side but never lose the panel, which
        # matters because everything must stay doable without gestures.
        #
        # The two panels share the right column through a plain layout rather
        # than a second splitter. A splitter hands out the sizes it was last
        # given and does not ask again when a child shrinks, so folding a form
        # away freed nothing: the box shrank and left the gap behind as
        # padding. A layout re-reads what each side needs, so the action panel
        # takes exactly the height of its forms and the vector list takes
        # everything that is left - which is all the old splitter handle was
        # ever dragged to do.
        self.action_panel = ActionPanel(self._store)
        self.info_panel = InfoPanel(self._store)
        panels = QWidget(self)
        panels_layout = QVBoxLayout(panels)
        panels_layout.setContentsMargins(0, 0, 0, 0)
        panels_layout.addWidget(self.action_panel)
        panels_layout.addWidget(self.info_panel, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(frame)
        splitter.addWidget(panels)
        splitter.setStretchFactor(0, 1)
        splitter.setSizes([WINDOW_WIDTH - PANEL_WIDTH, PANEL_WIDTH])
        self.setCentralWidget(splitter)

        # The small xyz marker in the corner. It is a camera widget rather
        # than part of the scene, so it turns as the view turns and says
        # which way is which even when the axes run off the edge of the view.
        self.plotter.add_axes()

        # The scene draws the world the vectors live in, and resizes it to
        # fit them. It redraws whenever the store changes, which is exactly
        # when `interaction-spec.md` section 3 allows the scene to rescale.
        self._result = None
        # What the head-to-tail animation is currently explaining, if anything.
        self._chain_terms: tuple = ()
        self._chain_result = None
        self.scene = Scene(self.plotter)
        self.vectors = VectorActors(self.plotter)
        # What a vector is made of, drawn only for the vectors that asked
        # for it (F-13a). Separate from the arrows, because the two answer
        # different questions and are switched on and off independently.
        self.overlays = ComponentOverlays(self.plotter)
        # The shadows on the three planes, switched on separately from the
        # components: the two answer different questions about a vector.
        self.projections = ProjectionOverlays(self.plotter)
        # The temporary operation result, drawn in the one reserved colour.
        # It is not a vector, so it gets its own actor rather than being
        # pushed through `VectorActors`.
        self.result = ResultActor(self.plotter)
        # When an input vector changes, the result arrow slides to its new
        # value over 150 ms rather than jumping (`interaction-spec.md` 10).
        self._result_transition = ComponentTransition(self._draw_result_at, self)
        # The head-to-tail explanation (F-15). It reports where each vector
        # should be *drawn* and how much of the resultant to show; nothing it
        # does reaches the store, which is what makes "the animation does not
        # permanently move or change any vector" true by construction.
        self._head_to_tail = HeadToTail(
            on_frame=self._draw_chain_frame,
            on_finished=self._on_animation_finished,
            parent=self,
        )
        self.info_panel.show_how_requested.connect(self._play_head_to_tail)
        self._store.subscribe(self._on_store_changed)

        self._build_toolbar()
        self._on_store_changed()

        # Shut the plotter down as the window closes, not after.
        self.signal_close.connect(self.plotter.close)

    def _build_toolbar(self) -> None:
        """The view controls, and undo.

        Undo and redo are the one thing here that changes vectors rather than
        the view. F-19 originally put them in the panel; the criterion was
        amended at G2.8 because the panel's height is what the vector list
        competes for, and because a toolbar is where a student reaches for
        undo without being told.
        """
        toolbar = QToolBar("View", self)
        toolbar.setMovable(False)

        reset = toolbar.addAction("Reset view")
        reset.setToolTip("Return the camera to the default angle, showing all three axes")
        reset.triggered.connect(self.scene.reset_view)

        toolbar.addSeparator()

        # Looking straight down an axis is what makes a vector readable: the
        # axis facing the student collapses to a point, and the other two are
        # seen without foreshortening.
        for name, hint in VIEW_HINTS.items():
            action = toolbar.addAction(name)
            action.setToolTip(hint)
            # `name` is bound now rather than read at click time, so each
            # button keeps the view it was made for.
            action.triggered.connect(
                lambda _checked=False, view=name: self.scene.set_view(view)
            )

        toolbar.addSeparator()

        self._undo = toolbar.addAction("Undo")
        self._undo.setToolTip("Take back the last change to the vectors (Ctrl+Z)")
        self._undo.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo.triggered.connect(self._on_undo)

        self._redo = toolbar.addAction("Redo")
        self._redo.setToolTip("Put back a change that was undone (Ctrl+Y)")
        self._redo.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo.triggered.connect(self._on_redo)

        self.addToolBar(toolbar)

    def _play_head_to_tail(self) -> None:
        """Start the explanation for the result currently showing (F-15)."""
        result = self._store.result
        if result is None:
            return

        # Not the source vectors as they are: a difference is laid out as
        # A followed by B reversed, so the chain ends on the answer. The
        # operation decides, in `actions.chain_terms`.
        terms = actions.chain_terms(self._store, result)
        if not terms:
            return

        self._chain_terms = terms
        self._chain_result = result
        # The overlays are drawn at a vector's real position, so a vector
        # showing its components would slide away and leave them behind at the
        # origin. They come back when the animation ends.
        self.overlays.draw((), None)
        self.projections.draw((), None)
        self._head_to_tail.play([term.components for term in terms])
        self.info_panel.refresh(
            self._store.vectors,
            self._store.active_name,
            self._store.selected,
            None,
            None,
            result,
            self._store.result_error,
            can_save_result=self._store.count < naming.MAX_VECTORS,
            can_show_result=False,
        )

    def _draw_chain_frame(
        self, tails: tuple[tuple[float, float, float], ...], drawn: float
    ) -> None:
        """Draw one frame of the chain: the vectors moved, the sum part-grown.

        The vectors drawn here are `replace`d copies carrying a different
        tail. `Vector` has stored a tail since G1.1 so that free vectors could
        be added after the MVP; that field is what lets the chain be drawn
        without the store ever holding a moved vector.
        """
        if self._chain_result is None:
            return

        moved = []
        labels = {}
        for term, tail in zip(self._chain_terms, tails):
            vector = self._store.get(term.source)
            if vector is None:
                return
            moved.append(replace(vector, components=term.components, tail=tail))
            labels[term.source] = term.label
        self.vectors.draw(moved, None, labels)

        # The resultant grows from the origin along its own line.
        grown = tuple(value * drawn for value in self._chain_result.components)
        self.result.draw(
            None if drawn <= 0.0 else replace(self._chain_result, components=grown)
        )
        self.plotter.render()

    def _on_animation_finished(self) -> None:
        """Put the real scene back once the animation stops or is cancelled."""
        self._chain_terms = ()
        self._chain_result = None
        self._result_transition.cancel()
        self._on_store_changed()

    def _draw_result_at(self, components: tuple[float, float, float]) -> None:
        """Draw the result arrow partway through its transition.

        Called for each step of the animation, and once directly when a
        result first appears. The result in the store keeps its real
        components throughout: only what is drawn moves, so nothing the info
        panel shows is ever a halfway value.
        """
        if self._result is None:
            return
        self.result.draw(replace(self._result, components=components))
        self.plotter.render()

    def _on_undo(self) -> None:
        """Undo, unless the student is typing.

        A focused text field keeps Ctrl+Z for its own text, which is what
        every other application does: the shortcut undoes whatever you are
        currently doing. Pressing the toolbar button moves focus away from
        the field first, so the button is never caught by this.
        """
        if isinstance(self.focusWidget(), QLineEdit):
            self.focusWidget().undo()
            return
        actions.undo(self._store)

    def _on_redo(self) -> None:
        if isinstance(self.focusWidget(), QLineEdit):
            self.focusWidget().redo()
            return
        actions.redo(self._store)

    def _on_store_changed(self) -> None:
        """Bring everything back in step after a change to the vectors.

        This is the only place that listens to the store. The panels and the
        3D view are told from here rather than subscribing for themselves,
        so there is one order of events and one place to look for it.
        """
        # The world is resized first, then the vectors are drawn into it, so
        # a vector that made the scene grow is never drawn against the old
        # grid even for one frame.
        # Anything that changes the vectors ends the explanation. Rather
        # than teaching the animation about edits, deletions and undo, the
        # rule is that the store wins and the real scene is redrawn.
        if self._head_to_tail.is_playing:
            self._head_to_tail.cancel()
            return

        vectors = self._store.vectors
        active = self._store.active_name
        result = self._store.result
        # The world is sized to the result as well as to the vectors: a
        # resultant is longer than either of its parts when they point the
        # same way (`interaction-spec.md` section 3).
        self.scene.update_for(vectors, result)
        self.vectors.draw(vectors, active)
        self.overlays.draw(vectors, self._store.components_shown)
        self.projections.draw(vectors, self._store.projections_shown)

        # The arrow is animated to its new components; everything else is
        # already where it belongs. `move_to` renders each step, so this is
        # also what renders the vectors drawn just above.
        self._result = result
        if result is None:
            self._result_transition.cancel()
            self.result.draw(None)
            self.plotter.render()
        else:
            self._result_transition.move_to(result.components)

        self.info_panel.refresh(
            vectors,
            active,
            self._store.selected,
            self._store.components_shown,
            self._store.projections_shown,
            result,
            self._store.result_error,
            can_save_result=self._store.count < naming.MAX_VECTORS,
            can_show_result=not self._head_to_tail.is_playing,
        )
        self.action_panel.refresh()
        self._undo.setEnabled(self._store.history.can_undo)
        self._redo.setEnabled(self._store.history.can_redo)

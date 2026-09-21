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

from PySide6.QtCore import Qt
from pyvistaqt import MainWindow, QtInteractor
from PySide6.QtWidgets import QFrame, QSplitter, QToolBar, QVBoxLayout

from vectra3d.render.scene import Scene
from vectra3d.render.vector_actor import VectorActors
from vectra3d.state.store import VectorStore
from vectra3d.ui.action_panel import ActionPanel

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
        layout.addWidget(self.plotter.interactor)

        # The 3D view on the left, the panels on the right. A splitter lets
        # the student widen either side but never lose the panel, which
        # matters because everything must stay doable without gestures.
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(frame)
        self.action_panel = ActionPanel(self._store)
        splitter.addWidget(self.action_panel)
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
        self.scene = Scene(self.plotter)
        self.vectors = VectorActors(self.plotter)
        self._store.subscribe(self._on_store_changed)

        self._build_toolbar()

        # Shut the plotter down as the window closes, not after.
        self.signal_close.connect(self.plotter.close)

    def _build_toolbar(self) -> None:
        """The view controls. Vector actions get their own panel in G1.3."""
        toolbar = QToolBar("View", self)
        toolbar.setMovable(False)
        reset = toolbar.addAction("Reset view")
        reset.setToolTip("Return the camera to the default angle")
        reset.triggered.connect(self.scene.reset_view)
        self.addToolBar(toolbar)

    def _on_store_changed(self) -> None:
        # The world is resized first, then the vectors are drawn into it, so
        # a vector that made the scene grow is never drawn against the old
        # grid even for one frame.
        vectors = self._store.vectors
        self.scene.update_for(vectors)
        self.vectors.draw(vectors, self._store.active_name)

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

from pyvistaqt import MainWindow, QtInteractor
from PySide6.QtWidgets import QFrame, QVBoxLayout

WINDOW_TITLE = "Vectra3D"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800

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
    """The application window. Currently just an empty, rotatable 3D view."""

    def __init__(self) -> None:
        super().__init__()

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
        self.setCentralWidget(frame)

        # The small xyz marker in the corner. It is a camera widget, not part
        # of the scene, so it turns as the view turns and shows which way is
        # which. The scene's own axes and grid arrive with the 3D scene (F-01).
        self.plotter.add_axes()

        # Shut the plotter down as the window closes, not after.
        self.signal_close.connect(self.plotter.close)

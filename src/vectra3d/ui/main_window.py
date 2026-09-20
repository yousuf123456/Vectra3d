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

# PyVista defaults to 8x multisampling, which costs about half the frame rate
# on the integrated graphics this app targets (measured: 33 fps against 60 on
# Intel HD Graphics 620). FXAA smooths edges as a single screen-space pass
# instead, which measured as free, so the view stays at the display's 60 fps
# and thin lines and arrows still look clean.
MULTI_SAMPLES = 0


class VectraMainWindow(MainWindow):
    """The application window. Currently just an empty, rotatable 3D view."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        frame = QFrame(self)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = QtInteractor(frame, multi_samples=MULTI_SAMPLES)
        self.plotter.enable_anti_aliasing("fxaa")
        layout.addWidget(self.plotter.interactor)
        self.setCentralWidget(frame)

        # The small xyz marker in the corner. It is a camera widget, not part
        # of the scene, so it turns as the view turns and shows which way is
        # which. The scene's own axes and grid arrive with the 3D scene (F-01).
        self.plotter.add_axes()

        # Shut the plotter down as the window closes, not after.
        self.signal_close.connect(self.plotter.close)

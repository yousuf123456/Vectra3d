"""Starts the application.

`QT_API` is set before anything imports pyvistaqt. pyvistaqt reaches Qt through
qtpy, which decides at import time which Qt binding to use based on this
variable and on what happens to be installed. Setting it explicitly is what
guarantees PySide6 is used, rather than whichever binding qtpy finds first.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.ui.main_window import VectraMainWindow  # noqa: E402


def main() -> int:
    """Open the main window and run until the user closes it."""
    app = QApplication([])

    window = VectraMainWindow()
    window.show()

    return app.exec()

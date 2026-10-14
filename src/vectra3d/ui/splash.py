"""The loading window shown while the app starts.

Found on a second laptop at G6.2: the app takes about 25 seconds to load its
libraries - the 3D engine about 11, hand tracking about 11 - and nothing was
on screen meanwhile, so it looked as if double-clicking had done nothing.

This module imports only Qt, so it can be shown about a second after the
program starts, before the slow parts load. It is drawn by hand on a pixmap
rather than built from widgets: the app's stylesheet and the main window do
not exist yet.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QSplashScreen

from vectra3d.ui import theme

WIDTH, HEIGHT = 420, 220
ICON_SIZE = 72
TITLE = "Vectra3D"
SUBTITLE = "3D vectors you can move with your hands"


def _picture(icon: QIcon) -> QPixmap:
    """The splash's still part: icon, name and a one-line description."""
    pixmap = QPixmap(WIDTH, HEIGHT)
    pixmap.fill(QColor(theme.SCENE_BACKGROUND))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.drawPixmap((WIDTH - ICON_SIZE) // 2, 28, icon.pixmap(ICON_SIZE, ICON_SIZE))

    title = QFont()
    title.setPointSize(20)
    title.setBold(True)
    painter.setFont(title)
    painter.setPen(QColor(theme.ACTIVE_BORDER))
    painter.drawText(QRect(0, 108, WIDTH, 36), Qt.AlignmentFlag.AlignHCenter, TITLE)

    subtitle = QFont()
    subtitle.setPointSize(10)
    painter.setFont(subtitle)
    painter.setPen(QColor(theme.MUTED_TEXT))
    painter.drawText(QRect(0, 146, WIDTH, 24), Qt.AlignmentFlag.AlignHCenter, SUBTITLE)

    # Frameless, and nearly white: the border keeps it from vanishing
    # against a light desktop.
    painter.setPen(QColor(theme.CARD_BORDER))
    painter.drawRect(0, 0, WIDTH - 1, HEIGHT - 1)
    painter.end()
    return pixmap


class LoadingSplash(QSplashScreen):
    """A frameless window with the app's name and what is loading now."""

    def __init__(self, icon: QIcon) -> None:
        super().__init__(_picture(icon))
        font = QFont()
        font.setPointSize(10)
        self.setFont(font)

    def say(self, text: str) -> None:
        """Show what is loading now, and paint it before the slow part starts.

        The loading that follows holds the main thread for seconds at a time,
        so nothing repaints during it: the text has to be on screen first.
        """
        self.showMessage(
            text,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
            QColor(theme.MUTED_TEXT),
        )
        QApplication.processEvents()

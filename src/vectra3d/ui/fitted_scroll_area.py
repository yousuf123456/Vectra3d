"""A scroll area that asks for its contents' full height.

Holds the action panel's forms. Without a scroll area they set the window's
minimum height - 830px with all three boxes open, against 728px of usable
height on a 1366x768 laptop - so the window grew past the bottom of the screen
(found at G4.1, when the camera strip at the bottom was what disappeared).

A plain `QScrollArea` does not solve that on its own: it asks the layout for a
small fixed size whatever it holds, so the forms would scroll even on a tall
screen. This one asks for exactly what its contents need. With room, it is
never squeezed and never scrolls; without, it gives way and scrolls.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QWidget


class FittedScrollArea(QScrollArea):
    def __init__(self, content: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWidget(content)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # A scroll area is not told when its contents change what they need -
        # a box folded, a card added. Without this it would keep asking for
        # the old height, the same fault the old panel splitter had.
        content.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
            self.updateGeometry()
        return super().eventFilter(watched, event)

    def sizeHint(self) -> QSize:
        return self.widget().sizeHint()

    def minimumSizeHint(self) -> QSize:
        # As wide as the contents need plus room for the scroll bar, and no
        # height of its own: when space is short, this is what scrolls.
        return QSize(
            self.widget().minimumSizeHint().width()
            + self.verticalScrollBar().sizeHint().width(),
            0,
        )

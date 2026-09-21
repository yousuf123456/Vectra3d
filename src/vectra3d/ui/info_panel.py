"""The info panel: every vector, with its colour and its numbers (F-11).

Almost display only. The one thing it changes is deleting a vector (F-10),
which lives here because the card is the thing the student is looking at when
they decide to remove it, and because it works before clicking a vector to
make it active arrives with F-05a in G2.2.

Each vector is a card rather than a row in a table. The panel is a narrow
column, and by G2.3 every vector shows a magnitude, three direction angles, a
unit vector and a lock state as well as its components. That is about twelve
values, which a table would have to scroll sideways to reach.

The list is rebuilt from scratch on every change rather than updated in
place. With at most ten cards that is cheaper than working out what moved,
and it cannot drift out of step with the store.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from vectra3d.core.formatting import format_number
from vectra3d.state import actions, naming
from vectra3d.state.models import Vector
from vectra3d.state.store import VectorStore

EMPTY_TEXT = "No vectors yet — create one above."

# The tint behind the active vector's card, matching the halo on its arrow.
ACTIVE_BACKGROUND = "#EEF3F8"
ACTIVE_BORDER = "#8FA9C2"
CARD_BORDER = "#DDDDDD"

SWATCH_SIZE = 12
AXIS_LABELS = ("x", "y", "z")


def card_values(vector: Vector) -> list[tuple[str, str]]:
    """The labelled numbers shown on one card, in display form.

    Separate from the widgets so what a card says can be tested without
    opening a window.
    """
    return [
        (axis, format_number(value))
        for axis, value in zip(AXIS_LABELS, vector.components)
    ]


class InfoPanel(QWidget):
    """The list of vectors currently in the scene."""

    def __init__(self, store: VectorStore) -> None:
        super().__init__()
        self._store = store

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Vectors")
        title.setStyleSheet("font-weight: bold;")
        outer.addWidget(title)

        self._cards = QWidget()
        self._cards_layout = QVBoxLayout(self._cards)
        self._cards_layout.setContentsMargins(0, 0, 0, 0)
        self._cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll = QScrollArea()
        scroll.setWidget(self._cards)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        self.refresh((), None)

    def refresh(self, vectors: Sequence[Vector], active_name: str | None) -> None:
        """Rebuild the list to match the store."""
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not vectors:
            empty = QLabel(EMPTY_TEXT)
            empty.setWordWrap(True)
            empty.setStyleSheet("color: #666666;")
            self._cards_layout.addWidget(empty)
            return

        for vector in vectors:
            self._cards_layout.addWidget(
                _build_card(vector, vector.name == active_name, self._delete)
            )

    def _delete(self, name: str) -> None:
        actions.delete_vector(self._store, name)


def _build_card(
    vector: Vector, is_active: bool, on_delete: Callable[[str], None]
) -> QWidget:
    """One vector's card: its name and colour, then its components."""
    color = naming.color_for(vector.name)

    card = QFrame()
    border = ACTIVE_BORDER if is_active else CARD_BORDER
    background = ACTIVE_BACKGROUND if is_active else "transparent"
    card.setStyleSheet(
        f"QFrame {{ border: 1px solid {border};"
        f" border-radius: 4px; background: {background}; }}"
    )

    layout = QGridLayout(card)
    layout.setContentsMargins(8, 6, 8, 6)

    swatch = QLabel()
    swatch.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
    swatch.setStyleSheet(f"background: {color}; border: none; border-radius: 2px;")
    layout.addWidget(swatch, 0, 0)

    name = QLabel(vector.name)
    name.setStyleSheet("font-weight: bold; border: none;")
    layout.addWidget(name, 0, 1)
    layout.setColumnStretch(1, 1)

    # The name is bound into the call rather than read back from the widget,
    # so a card can only ever delete the vector it is showing.
    delete = QToolButton()
    delete.setText("✕")
    delete.setToolTip(f"Delete vector {vector.name}")
    delete.setAutoRaise(True)
    delete.setStyleSheet("border: none; color: #666666;")
    delete.clicked.connect(lambda: on_delete(vector.name))
    layout.addWidget(delete, 0, 2)

    for row, (axis, text) in enumerate(card_values(vector), start=1):
        label = QLabel(axis)
        label.setStyleSheet("color: #666666; border: none;")
        value = QLabel(text)
        value.setStyleSheet("border: none;")
        value.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(label, row, 0, 1, 2)
        layout.addWidget(value, row, 2)

    return card

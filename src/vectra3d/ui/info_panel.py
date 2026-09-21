"""The info panel: every vector, with its colour and its numbers (F-11).

The cards are also where a vector is picked. Clicking one makes that vector
active; its tick box marks it for an operation, and the two are independent
(F-05a). Deleting lives here too (F-10), because the card is the thing the
student is looking at when they decide to remove it.

None of that state is kept here. Each card binds its vector's name into a
callback that calls `state/actions.py`, and the panel is told what to show
through `refresh()`. That matters because the cards are rebuilt from scratch
on every change, so anything remembered in a widget would not survive.

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
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox,
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
from vectra3d.ui import theme

EMPTY_TEXT = "No vectors yet — create one above."

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
        title.setProperty("role", "title")
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

    def refresh(
        self,
        vectors: Sequence[Vector],
        active_name: str | None,
        selected: Sequence[str] = (),
    ) -> None:
        """Rebuild the list to match the store."""
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        if not vectors:
            empty = QLabel(EMPTY_TEXT)
            empty.setWordWrap(True)
            empty.setStyleSheet(f"color: {theme.MUTED_TEXT};")
            self._cards_layout.addWidget(empty)
            return

        ticked = set(selected)
        for vector in vectors:
            self._cards_layout.addWidget(
                _build_card(
                    vector,
                    is_active=vector.name == active_name,
                    is_selected=vector.name in ticked,
                    on_delete=self._delete,
                    on_activate=self._activate,
                    on_toggle=self._toggle,
                )
            )

    def _delete(self, name: str) -> None:
        actions.delete_vector(self._store, name)

    def _activate(self, name: str) -> None:
        actions.set_active(self._store, name)

    def _toggle(self, name: str) -> None:
        actions.toggle_selected(self._store, name)


class _Card(QFrame):
    """A vector's card, which activates that vector when clicked.

    Activation is handled here rather than with a button behind the contents
    so that the checkbox and the delete button keep their own clicks: a child
    widget consumes the press before it ever reaches this handler. That is
    what keeps ticking and activating independent (F-05a).
    """

    def __init__(self, name: str, on_activate: Callable[[str], None]) -> None:
        super().__init__()
        self._name = name
        self._on_activate = on_activate
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_activate(self._name)
        super().mousePressEvent(event)


def _build_card(
    vector: Vector,
    *,
    is_active: bool,
    is_selected: bool,
    on_delete: Callable[[str], None],
    on_activate: Callable[[str], None],
    on_toggle: Callable[[str], None],
) -> QWidget:
    """One vector's card: a tick box, its name and colour, then its components."""
    color = naming.color_for(vector.name)

    card = _Card(vector.name, on_activate)
    border = theme.ACTIVE_BORDER if is_active else theme.CARD_BORDER
    background = theme.ACTIVE_BACKGROUND if is_active else theme.CARD_BACKGROUND
    card.setStyleSheet(
        f"QFrame {{ border: 1px solid {border};"
        f" border-radius: {theme.CARD_RADIUS}px; background: {background}; }}"
    )

    layout = QGridLayout(card)
    layout.setContentsMargins(theme.GAP, theme.GAP_SMALL, theme.GAP, theme.GAP_SMALL)
    layout.setHorizontalSpacing(theme.GAP_SMALL)

    # The tick box comes first, so the ticks form a column that can be read
    # down the panel at a glance when picking vectors for an operation.
    tick = QCheckBox()
    tick.setChecked(is_selected)
    tick.setToolTip(f"Include vector {vector.name} in an operation")
    tick.clicked.connect(lambda: on_toggle(vector.name))
    layout.addWidget(tick, 0, 0)

    swatch = QLabel()
    swatch.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
    swatch.setStyleSheet(f"background: {color}; border: none; border-radius: 3px;")
    layout.addWidget(swatch, 0, 1)

    name = QLabel(vector.name)
    name.setStyleSheet("font-weight: 600; border: none;")
    layout.addWidget(name, 0, 2)
    layout.setColumnStretch(2, 1)

    # The name is bound into the call rather than read back from the widget,
    # so a card can only ever delete the vector it is showing.
    delete = QToolButton()
    delete.setText("✕")
    delete.setToolTip(f"Delete vector {vector.name}")
    delete.setAutoRaise(True)
    delete.setStyleSheet(f"border: none; color: {theme.MUTED_TEXT};")
    delete.clicked.connect(lambda: on_delete(vector.name))
    layout.addWidget(delete, 0, 3)

    for row, (axis, text) in enumerate(card_values(vector), start=1):
        label = QLabel(axis)
        label.setStyleSheet(f"color: {theme.MUTED_TEXT}; border: none;")
        value = QLabel(text)
        value.setStyleSheet("border: none;")
        value.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(label, row, 0, 1, 3)
        layout.addWidget(value, row, 3)

    return card

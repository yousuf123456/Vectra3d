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
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from vectra3d.core.formatting import (
    UNDEFINED_NOTE,
    format_angle,
    format_number,
    format_triple,
)
from vectra3d.core.vector_math import direction_angles, magnitude, unit_vector
from vectra3d.state import actions, naming
from vectra3d.state.models import Result, Vector
from vectra3d.state.store import VectorStore
from vectra3d.ui import theme

EMPTY_TEXT = "No vectors yet — create one above."

SWATCH_SIZE = 12
AXIS_LABELS = ("x", "y", "z")
ANGLE_LABELS = ("α", "β", "γ")

# The lock control is on every card, not only on locked ones. Until G2.5
# nothing could set the flag, so an indicator was all it could be; now it is
# the control, and hiding it on unlocked cards would mean locking from one
# panel and reading the result in another.
#
# A word rather than a padlock glyph. The first version used 🔒 and 🔓, and
# the two were not tellable apart at this size: Windows draws them as colour
# emoji, which are bitmaps, so they ignore the muting that was supposed to
# separate the two states. Text obeys colour and weight, so the difference
# survives whatever font the machine has.
LOCKED_TEXT = "Locked"
UNLOCKED_TEXT = "Lock"

# The theme pads tool buttons for a toolbar, where they stand alone. In a
# card header, four of them in a 300px column, that padding is what decides
# whether the card fits: "Locked" asked for 109px of the 282 available until
# this was trimmed.
HEADER_BUTTON_STYLE = "border: none; padding: 0px 2px; margin: 0px;"

# The display toggles sit on their own row under the numbers rather than in
# the header, which already carries five controls in a 300px column. The row
# costs about 24px per card - roughly three quarters of a card across a full
# list - and buys the thing the action panel could not: which vectors have an
# overlay on is a column that can be read down without activating each one.
# G2.7's projections toggle joins this row.
#
# Only one vector shows its components at a time, so switching it on here
# switches it off wherever it was; `VectorStore` explains why.
COMPONENTS_TEXT = "Components"
PROJECTIONS_TEXT = "Projections"


def card_values(vector: Vector) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """The labelled numbers on a vector's card. See `values_for`."""
    return values_for(vector.components)


def values_for(
    components: tuple[float, float, float],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """The labelled numbers on one card, in display form, as two columns.

    The left column is what the vector *is* - its components and how long it
    is. The right column is which way it points - its three direction angles
    and its unit vector. Splitting them is what lets about a dozen values sit
    in a 300px panel without a card becoming a column of twelve rows.

    Everything undefined for the zero vector comes back as an em dash, which
    `core/formatting.py` decides; the maths hands back `None` and this never
    has to ask whether a vector is zero.

    Separate from the widgets so what a card says can be tested without
    opening a window.

    Takes components rather than a vector, because a temporary result shows
    exactly the same numbers as a vector does (`features.md`, global rules
    for operation results) while not being one.
    """
    angles = direction_angles(components)
    unit = unit_vector(components)

    left = [
        (axis, format_number(value)) for axis, value in zip(AXIS_LABELS, components)
    ]
    left.append(("|v|", format_number(magnitude(components))))

    right = [
        (label, format_angle(None if angles is None else angles[index]))
        for index, label in enumerate(ANGLE_LABELS)
    ]
    right.append(("û", format_triple(unit)))

    return left, right


def lock_label(locked: bool) -> str:
    """What the lock control reads.

    A state when locked and an offer when not, which is what makes the two
    tellable apart at a glance: "Locked" is a fact about this vector,
    "Lock" is a button waiting to be pressed.
    """
    return LOCKED_TEXT if locked else UNLOCKED_TEXT


def lock_tooltip(name: str, locked: bool) -> str:
    """What the padlock says it will do, rather than what it is showing.

    A control is read as a verb: the tooltip on a locked vector offers to
    unlock it. Which state it is in is already said by the icon.
    """
    if locked:
        return f"Unlock vector {name} so it can be changed"
    return f"Lock vector {name} so it cannot be changed or deleted"


def delete_tooltip(name: str, locked: bool) -> str:
    """What the delete button says, including why it is unavailable.

    A locked vector's button is greyed rather than removed or left to fail,
    so the tooltip is the only place the rule can be explained - and the
    padlock that lifts it is immediately beside it.
    """
    if locked:
        return f"Vector {name} is locked. Unlock it to delete."
    return f"Delete vector {name}"


def toggle_style(on: bool) -> str:
    """How a display toggle looks in each state.

    On is the accent colour and bold, the same treatment "Locked" uses, so
    one glance down the list answers "what is switched on here?" whatever the
    switch is. Off is muted, an offer rather than a state.
    """
    if on:
        return f"{HEADER_BUTTON_STYLE} color: {theme.ACTIVE_BORDER}; font-weight: 600;"
    return f"{HEADER_BUTTON_STYLE} color: {theme.MUTED_TEXT};"


def components_tooltip(name: str, shown: bool) -> str:
    """What the components toggle offers to do next."""
    if shown:
        return f"Hide vector {name}'s x, y and z parts"
    return f"Show vector {name} resolved into its x, y and z parts"


def projections_tooltip(name: str, shown: bool) -> str:
    """What the projections toggle offers to do next."""
    if shown:
        return f"Hide vector {name}'s shadows"
    return f"Show vector {name}'s shadows on the XY, YZ and XZ planes"


def card_note(vector: Vector) -> str | None:
    """The line explaining why a card has dashes on it, or None.

    On the card rather than once for the panel, because a card is meant to
    be read on its own and a panel-level note could not say which of ten
    vectors it was about.
    """
    if magnitude(vector.components) == 0.0:
        return UNDEFINED_NOTE
    return None


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
        components_shown: str | None = None,
        projections_shown: str | None = None,
        result: Result | None = None,
        result_error: str | None = None,
        can_save_result: bool = True,
    ) -> None:
        """Rebuild the list to match the store."""
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        # The result sits above the vectors, where the answer to what the
        # student just asked for is the first thing they see, and where it
        # does not move as vectors are added and removed below it.
        if result is not None:
            self._cards_layout.addWidget(
                _build_result_card(
                    result, on_save=self._save_result, can_save=can_save_result
                )
            )
        elif result_error is not None:
            self._cards_layout.addWidget(_build_result_message(result_error))

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
                    on_toggle_lock=self._toggle_lock,
                    on_toggle_components=self._toggle_components,
                    on_toggle_projections=self._toggle_projections,
                    shows_components=vector.name == components_shown,
                    shows_projections=vector.name == projections_shown,
                )
            )

    def _delete(self, name: str) -> None:
        actions.delete_vector(self._store, name)

    def _activate(self, name: str) -> None:
        actions.set_active(self._store, name)

    def _toggle(self, name: str) -> None:
        actions.toggle_selected(self._store, name)

    def _toggle_lock(self, name: str) -> None:
        actions.toggle_locked(self._store, name)

    def _toggle_components(self, name: str) -> None:
        actions.toggle_components(self._store, name)

    def _toggle_projections(self, name: str) -> None:
        actions.toggle_projections(self._store, name)

    def _save_result(self) -> None:
        actions.save_result_as_vector(self._store)


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
    on_toggle_lock: Callable[[str], None],
    on_toggle_components: Callable[[str], None],
    on_toggle_projections: Callable[[str], None],
    shows_components: bool,
    shows_projections: bool,
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

    # The header and the numbers are laid out separately. They used to share
    # one grid, which meant the stretch that pushes the delete button to the
    # right edge was also stretching a column of the table below it, opening
    # a gap between each angle and its value.
    outer = QVBoxLayout(card)
    outer.setContentsMargins(theme.GAP, theme.GAP_SMALL, theme.GAP, theme.GAP_SMALL)
    outer.setSpacing(theme.GAP_SMALL)

    header = QHBoxLayout()
    header.setSpacing(theme.GAP_SMALL)

    # The tick box comes first, so the ticks form a column that can be read
    # down the panel at a glance when picking vectors for an operation.
    tick = QCheckBox()
    tick.setChecked(is_selected)
    tick.setToolTip(f"Include vector {vector.name} in an operation")
    tick.clicked.connect(lambda: on_toggle(vector.name))
    header.addWidget(tick)

    swatch = QLabel()
    swatch.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
    swatch.setStyleSheet(f"background: {color}; border: none; border-radius: 3px;")
    header.addWidget(swatch)

    name = QLabel(vector.name)
    name.setStyleSheet("font-weight: 600; border: none;")
    header.addWidget(name)
    header.addStretch(1)

    # Like the tick box, this is a child widget, so its click never reaches
    # the card underneath and locking a vector does not also activate it.
    lock = QToolButton()
    lock.setText(lock_label(vector.locked))
    lock.setToolTip(lock_tooltip(vector.name, vector.locked))
    lock.setAutoRaise(True)
    # "Lock" is muted and light: an offer, not a state worth noticing.
    # "Locked" is the card's accent colour and bold, because it is the
    # reason the card's other controls have stopped working.
    lock.setStyleSheet(toggle_style(vector.locked))
    lock.clicked.connect(lambda: on_toggle_lock(vector.name))
    header.addWidget(lock)

    # The name is bound into the call rather than read back from the widget,
    # so a card can only ever delete the vector it is showing.
    delete = QToolButton()
    delete.setText("✕")
    delete.setToolTip(delete_tooltip(vector.name, vector.locked))
    delete.setAutoRaise(True)
    delete.setEnabled(not vector.locked)
    delete.setStyleSheet(f"{HEADER_BUTTON_STYLE} color: {theme.MUTED_TEXT};")
    delete.clicked.connect(lambda: on_delete(vector.name))
    header.addWidget(delete)

    outer.addLayout(header)

    # Two pairs of columns: what the vector is on the left, which way it
    # points on the right. Each value sits directly against its own name, and
    # the space left over goes between the two pairs rather than inside them.
    values = QGridLayout()
    values.setHorizontalSpacing(theme.GAP_SMALL)
    values.setVerticalSpacing(2)
    values.setColumnStretch(2, 1)

    left, right = card_values(vector)
    for row, (name_text, value_text) in enumerate(left):
        values.addWidget(_key(name_text), row, 0)
        values.addWidget(_value(value_text), row, 1)
    for row, (name_text, value_text) in enumerate(right):
        values.addWidget(_key(name_text), row, 3)
        # Left-aligned, unlike the left column. The unit vector is far wider
        # than an angle, so right-aligning would size this column to the unit
        # vector and leave each angle stranded away from its own name. The
        # angles are all the same width, so they line up either way.
        values.addWidget(_value(value_text, align_right=False), row, 4)

    outer.addLayout(values)

    # The display toggles. A row of its own, so the header stays readable and
    # so G2.7 can add projections beside this without redesigning the card.
    toggles = QHBoxLayout()
    toggles.setContentsMargins(0, 0, 0, 0)
    toggles.setSpacing(theme.GAP_SMALL)

    components = QToolButton()
    components.setText(COMPONENTS_TEXT)
    components.setToolTip(components_tooltip(vector.name, shows_components))
    components.setAutoRaise(True)
    components.setStyleSheet(toggle_style(shows_components))
    components.clicked.connect(lambda: on_toggle_components(vector.name))
    toggles.addWidget(components)

    projections = QToolButton()
    projections.setText(PROJECTIONS_TEXT)
    projections.setToolTip(projections_tooltip(vector.name, shows_projections))
    projections.setAutoRaise(True)
    projections.setStyleSheet(toggle_style(shows_projections))
    projections.clicked.connect(lambda: on_toggle_projections(vector.name))
    toggles.addWidget(projections)

    toggles.addStretch(1)

    outer.addLayout(toggles)

    note = card_note(vector)
    if note is not None:
        text = QLabel(note)
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {theme.MUTED_TEXT}; border: none;")
        outer.addWidget(text)

    return card


def _key(text: str) -> QLabel:
    """The name of a value: the quieter half of the pair."""
    label = QLabel(text)
    label.setStyleSheet(f"color: {theme.MUTED_TEXT}; border: none;")
    return label


def _value(text: str, *, align_right: bool = True) -> QLabel:
    """The value itself.

    Right-aligned by default, so numbers of different widths line up down a
    column by their last digit. The right-hand column asks for left instead,
    for the reason given where it is built.
    """
    label = QLabel(text)
    label.setStyleSheet("border: none;")
    label.setAlignment(
        Qt.AlignmentFlag.AlignRight if align_right else Qt.AlignmentFlag.AlignLeft
    )
    return label


# What the Save button says, and why it might be refused. The limit message
# names the rule rather than just refusing, because a disabled button with no
# explanation reads as a broken one.
SAVE_TEXT = "Save as vector"
SAVE_TOOLTIP = "Keep this result as a vector of its own, with the next free letter"
SAVE_FULL_TOOLTIP = (
    f"There are already {naming.MAX_VECTORS} vectors. "
    "Delete one to save this result."
)


def _build_result_card(
    result: Result,
    *,
    on_save: Callable[[], None],
    can_save: bool,
) -> QWidget:
    """The temporary result's card: its expression, its numbers, and Save.

    Built apart from `_build_card` rather than by adding options to it. A
    result has no tick box, no lock, no delete and nothing to activate, and
    it has a Save button that a vector does not; threading five "only if this
    is a vector" conditions through one builder would make both harder to
    read than having two.
    """
    card = QFrame()
    card.setStyleSheet(
        f"QFrame {{ border: 1px solid {naming.RESULT_COLOR};"
        f" border-radius: {theme.CARD_RADIUS}px; background: {theme.CARD_BACKGROUND}; }}"
    )

    outer = QVBoxLayout(card)
    outer.setContentsMargins(theme.GAP, theme.GAP_SMALL, theme.GAP, theme.GAP_SMALL)
    outer.setSpacing(theme.GAP_SMALL)

    header = QHBoxLayout()
    header.setSpacing(theme.GAP_SMALL)

    # The same swatch a vector card carries, in the reserved colour, so the
    # black arrow in the 3D view is tied to this card without reading a word.
    swatch = QLabel()
    swatch.setFixedSize(SWATCH_SIZE, SWATCH_SIZE)
    swatch.setStyleSheet(
        f"background: {naming.RESULT_COLOR}; border: none; border-radius: 3px;"
    )
    header.addWidget(swatch)

    # The expression is the result's name: "A + B" says both what it is and
    # where it came from, which a letter could not.
    expression = QLabel(result.expression)
    expression.setStyleSheet("font-weight: 600; border: none;")
    header.addWidget(expression)
    header.addStretch(1)
    outer.addLayout(header)

    values = QGridLayout()
    values.setHorizontalSpacing(theme.GAP_SMALL)
    values.setVerticalSpacing(2)
    values.setColumnStretch(2, 1)

    left, right = values_for(result.components)
    for row, (name_text, value_text) in enumerate(left):
        values.addWidget(_key(name_text), row, 0)
        values.addWidget(_value(value_text), row, 1)
    for row, (name_text, value_text) in enumerate(right):
        values.addWidget(_key(name_text), row, 3)
        values.addWidget(_value(value_text, align_right=False), row, 4)
    outer.addLayout(values)

    save = QToolButton()
    save.setText(SAVE_TEXT)
    save.setEnabled(can_save)
    save.setToolTip(SAVE_TOOLTIP if can_save else SAVE_FULL_TOOLTIP)
    save.setAutoRaise(True)
    save.setStyleSheet(f"{HEADER_BUTTON_STYLE} color: {theme.ACTIVE_BORDER};")
    save.clicked.connect(lambda: on_save())
    outer.addWidget(save, alignment=Qt.AlignmentFlag.AlignLeft)

    return card


def _build_result_message(message: str) -> QWidget:
    """Why the result went away, where the result itself would have been.

    A result can disappear without the student touching it - editing a vector
    until the sum no longer fits in a number - and something vanishing with
    no explanation reads as a bug rather than as an answer.
    """
    label = QLabel(message)
    label.setWordWrap(True)
    label.setStyleSheet(f"color: {theme.ERROR_TEXT}; padding: {theme.GAP_SMALL}px;")
    return label

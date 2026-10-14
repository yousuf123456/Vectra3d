"""The action panel: typing exact vectors (F-04) and editing them (F-08).

Two boxes, one above the other. **New vector** makes a vector from what is
typed; **Edit vector** changes the active one. Both are always visible, so it
is never ambiguous whether pressing the button will add an eleventh vector or
change the one being looked at.

A vector can be entered either as components (x, y, z) or as a magnitude and
two angles, chosen with a toggle. Both boxes offer the same choice and the
same parsing rules, through the same `VectorForm` widget, and their toggles
move independently. Switching the toggle shows the other set of fields; it
does not convert what is typed into them. In the edit box that costs nothing,
because both sets are filled from the vector each time it changes.

Input is checked when the button is pressed rather than keystroke by
keystroke, so someone who types `3,5` is told what is wrong instead of having
the comma silently refused, and a half-typed `-` is never an error. That is
also what F-08's "changes apply immediately" means here: the moment Apply is
pressed the 3D view and the info panel show the new vector, with no further
confirmation.

The parsing, the field text and the rule for when the edit fields are refilled
are module-level functions, separate from the widgets, so they can be tested
without building a window.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from vectra3d import config
from vectra3d.core.formatting import format_number
from vectra3d.core.vector_math import (
    direction_angles,
    direction_cosine_sum,
    from_direction_angles,
    magnitude as vector_magnitude,
)
from vectra3d.state import actions, naming
from vectra3d.state.models import Point, Vector
from vectra3d.state.store import VectorStore
from vectra3d.render.scene import MAX_COMPONENT
from vectra3d.ui import theme
from vectra3d.ui.dialogs import confirm_clear_all

ERROR_STYLE = f"color: {theme.ERROR_TEXT};"

# What the Resultant button says while it cannot be pressed. A disabled
# button with no explanation reads as broken, and the rule it is waiting for
# - tick two or more - is not guessable from the button alone.
RESULTANT_HINT = "Tick two or more vectors to add them together."

# The typographic minus, matching how F-16 writes the operation and how a
# textbook prints it. Not the hyphen on the keyboard.
MINUS = "\u2212"
# Subtraction needs somewhere to subtract from, so it waits for a vector.
SUBTRACT_HINT = "Create a vector to subtract."

COMPONENTS_MODE = 0
ANGLES_MODE = 1

NO_VECTOR_HINT = "Create a vector first, or click one to edit it."
# What a student is told when an eleventh vector is asked for, by typing or by
# hand (F-04, F-03).
LIMIT_TEXT = (
    f"The scene already has the most vectors allowed "
    f"({naming.MAX_VECTORS}). Delete one to make room."
)
LOCKED_HINT = "Vector {name} is locked. Unlock it to edit."

# What the short field labels leave out: which axis each angle is measured
# from, said once beside the magnitude rather than in labels too wide for
# the row.
ANGLE_HINT = "α, β, γ from +x, +y, +z"

# The direction angles are typed as three numbers, but they belong to one
# direction only if cos²α + cos²β + cos²γ = 1 (`interaction-spec.md` 2.3).
# This much off is accepted, as rounding: textbook angles to a tenth of a
# degree, and the form's own two-decimal refill, stay well within it.
DIRECTION_COSINE_TOLERANCE = 0.01
ANGLE_NAMES = ("α", "β", "γ")

# Enough for a typed value like -123.45 without the three fields in a row
# squeezing each other out.
FIELD_MIN_WIDTH = 56



@dataclass(frozen=True)
class Parsed:
    """The outcome of reading the form: components, or why they are not valid."""

    components: tuple[float, float, float] | None = None
    error: str | None = None


def parse_number(text: str, name: str) -> tuple[float | None, str | None]:
    """Read one typed field, or say what is wrong with it.

    `float()` accepts more than it looks like it does: "nan", "inf", "-inf",
    and anything large enough to overflow, such as "1e400", all parse
    happily. None of them is a length a vector can have, and letting one
    through reaches the scene sizing, which has no extent that fits it.
    They are turned away here, at the only place typed numbers enter.

    A number that is merely *very large* is turned away here too, above
    `MAX_COMPONENT`. VTK holds point coordinates as 32-bit floats, so a
    vector beyond about 3.4e38 cannot be drawn at all: its geometry becomes
    infinity and the render fails. Typing 1e308 used to take the window down
    this way. Nothing a student does comes near the limit; it is here so the
    app says no instead of crashing.
    """
    text = text.strip()
    if not text:
        return None, f"Enter a value for {name}."

    try:
        value = float(text)
    except ValueError:
        return None, f"{name} must be a number. Use a dot for decimals, like 3.5."

    if math.isnan(value):
        return None, f"{name} must be a number. Use a dot for decimals, like 3.5."
    if math.isinf(value) or abs(value) > MAX_COMPONENT:
        return None, f"{name} is too large to use."

    return value, None


def parse_components(x: str, y: str, z: str) -> Parsed:
    """Read the x, y, z form."""
    values: list[float] = []
    for text, name in ((x, "x"), (y, "y"), (z, "z")):
        value, error = parse_number(text, name)
        if error is not None:
            return Parsed(error=error)
        values.append(value)

    if all(value == 0.0 for value in values):
        return Parsed(error="A vector needs a direction. All three values are zero.")

    return Parsed(components=(values[0], values[1], values[2]))


def parse_angles(length: str, alpha: str, beta: str, gamma: str) -> Parsed:
    """Read the magnitude and direction angles form.

    Each angle must be between 0° and 180°, and the three must fit together:
    cos²α + cos²β + cos²γ within `DIRECTION_COSINE_TOLERANCE` of 1. If they
    do not, the student is shown the sum their angles make, which says what
    is wrong and how far off it is.
    """
    values: list[float] = []
    names = ("the magnitude", *ANGLE_NAMES)
    for text, name in zip((length, alpha, beta, gamma), names):
        value, error = parse_number(text, name)
        if error is not None:
            return Parsed(error=error)
        values.append(value)

    magnitude, *angles = values
    if magnitude <= 0:
        return Parsed(error="The magnitude must be greater than 0.")
    for angle, name in zip(angles, ANGLE_NAMES):
        if not 0.0 <= angle <= 180.0:
            return Parsed(error=f"{name} must be between 0° and 180°.")

    total = direction_cosine_sum(*angles)
    if abs(total - 1.0) > DIRECTION_COSINE_TOLERANCE:
        return Parsed(
            error=(
                "These angles do not fit together: cos²α + cos²β + cos²γ = "
                f"{format_number(total, decimals=3)}, but it must be 1."
            )
        )

    return Parsed(components=from_direction_angles(magnitude, *angles))


def component_fields(components: Point) -> tuple[str, str, str]:
    """The x, y, z boxes' text for a vector, as the info panel would show it.

    Two decimals, not full precision. The form sits beside a card showing the
    same vector, and the two disagreeing would be worse than the rounding:
    a field reading 6.123233995736766e-17 says nothing a student can use.

    It does mean that pressing Apply without typing anything can round the
    stored value, which is the one place displayed text feeds back into the
    maths. What it rounds away is floating-point dust from the angle
    conversion, never a value anyone entered.
    """
    return (
        format_number(components[0]),
        format_number(components[1]),
        format_number(components[2]),
    )


def angle_fields(components: Point) -> tuple[str, str, str, str]:
    """The |v|, α, β, γ boxes' text for a vector, at the same two decimals.

    The zero vector has no direction, so every box reads 0.00 and Apply then
    refuses it with the usual "the magnitude must be greater than 0". A saved
    result that cancels out, `A - A`, is such a vector.
    """
    angles = direction_angles(components)
    if angles is None:
        return (format_number(0.0),) * 4

    return (format_number(vector_magnitude(components)), *map(format_number, angles))


def should_refill(shown: tuple[str, Point] | None, active: Vector | None) -> bool:
    """Whether the edit fields should be rewritten from the store.

    `shown` is the name and components the fields were last filled from.

    Every change to the store notifies every listener, including ones that
    have nothing to do with the vector being edited: ticking another card,
    deleting a different vector. Refilling on all of them would wipe
    half-typed text for no reason, so the form refills only when what it is
    showing is genuinely out of date - a different vector is active, or the
    active one has different components than the fields were filled from.

    That second case is what matters from G5: a vector steered by hand would
    otherwise leave stale numbers here, and Apply would quietly put it back
    where it was.
    """
    if active is None:
        return shown is not None
    return shown != (active.name, active.components)


class VectorForm(QWidget):
    """A mode toggle, three fields and a button: how a vector is typed.

    Used by both boxes. The button's text and what it does are given by the
    caller; everything about reading and filling the fields is the same for
    creating and for editing, and lives here so it exists once.
    """

    def __init__(self, button_text: str, on_submit: Callable[[], None]) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._by_components = QRadioButton("Components (x, y, z)")
        self._by_angles = QRadioButton("Magnitude + angles")
        self._by_components.setChecked(True)

        # The group is held on the widget so both buttons stay owned by it;
        # a QButtonGroup that goes out of scope stops enforcing exclusivity.
        self._mode = QButtonGroup(self)
        self._mode.addButton(self._by_components, COMPONENTS_MODE)
        self._mode.addButton(self._by_angles, ANGLES_MODE)
        layout.addWidget(self._by_components)
        layout.addWidget(self._by_angles)

        self._fields = QStackedWidget()
        self._x, self._y, self._z = QLineEdit(), QLineEdit(), QLineEdit()
        self._length = QLineEdit()
        self._angles = (QLineEdit(), QLineEdit(), QLineEdit())
        for field, name, axis in zip(self._angles, ANGLE_NAMES, "xyz"):
            field.setToolTip(f"{name}: the angle with the +{axis} axis, 0° to 180°")
        self._fields.addWidget(_field_row({"x": self._x, "y": self._y, "z": self._z}))
        self._fields.addWidget(_angle_rows(self._length, self._angles))
        self._mode.idToggled.connect(self._on_mode_changed)
        layout.addWidget(self._fields)

        # Enter in any field does what the button does. Qt only withholds
        # returnPressed when a validator refuses the text, and these fields
        # have none: they are read by `parse_number` when the form is
        # submitted, which is what lets it explain a bad value.
        for field in self._all_fields():
            field.returnPressed.connect(on_submit)

        button = QPushButton(button_text)
        button.clicked.connect(on_submit)
        layout.addWidget(button)

        # Hidden until there is something to say. A permanently present empty
        # label reserves a row of height in each box, which is height the
        # vector list needs.
        self._message = QLabel()
        self._message.setWordWrap(True)
        self._message.setStyleSheet(ERROR_STYLE)
        self._message.hide()
        layout.addWidget(self._message)

    def parsed(self) -> Parsed:
        """Read whichever set of fields is showing."""
        if self._by_components.isChecked():
            return parse_components(self._x.text(), self._y.text(), self._z.text())
        return parse_angles(
            self._length.text(), *(field.text() for field in self._angles)
        )

    def fill(self, components: Point) -> None:
        """Write a vector into both sets of fields.

        Both, not only the visible set, so switching the toggle shows the
        same vector said the other way rather than whatever was last left
        there.
        """
        for field, text in zip(
            (self._x, self._y, self._z), component_fields(components)
        ):
            field.setText(text)
        for field, text in zip(
            (self._length, *self._angles), angle_fields(components)
        ):
            field.setText(text)
        self.clear_message()

    def clear(self) -> None:
        """Empty every field, for when there is nothing to show."""
        for field in self._all_fields():
            field.clear()
        self.clear_message()

    def show_message(self, text: str) -> None:
        self._message.setText(text)
        self._message.show()

    def clear_message(self) -> None:
        self._message.clear()
        self._message.hide()

    def _all_fields(self) -> tuple[QLineEdit, ...]:
        return (self._x, self._y, self._z, self._length, *self._angles)

    def _on_mode_changed(self, index: int, checked: bool) -> None:
        if checked:
            self._fields.setCurrentIndex(index)
            self.clear_message()


class CollapsibleBox(QGroupBox):
    """A titled box whose contents can be folded out of the way.

    The panel holds two forms, and at 223px each they left room for two of
    the ten vector cards in an 800px window. Folding the form not in use
    gives that space straight back to the list.

    The title is a flat button rather than the group box's own title text,
    because a QGroupBox title cannot be clicked. Qt's checkable group box
    puts a checkbox there, but unchecking it *disables* the contents rather
    than hiding them - a different thing, which saves no space and would
    fight the rule that disables this box for a locked vector.

    Boxes start open: nothing is hidden until the student chooses to hide
    it, and the fold is theirs to undo. The one exception is the gesture
    settings, which are rarely changed and would otherwise take room from
    the vector list on every launch.
    """

    def __init__(self, title: str, expanded: bool = True) -> None:
        super().__init__()

        self._header = QToolButton()
        self._header.setText(title)
        self._header.setCheckable(True)
        self._header.setChecked(expanded)
        self._header.setAutoRaise(True)
        self._header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._header.setStyleSheet("QToolButton { border: none; font-weight: 600; }")
        self._header.toggled.connect(self._fold)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.GAP_SMALL, theme.GAP_SMALL, theme.GAP_SMALL, theme.GAP_SMALL)
        layout.setSpacing(theme.GAP_SMALL)
        layout.addWidget(self._header)
        layout.addWidget(self._content)

        self._content.setVisible(expanded)
        self._update_arrow()

    def add(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def set_title(self, text: str) -> None:
        self._header.setText(text)

    def set_content_enabled(self, enabled: bool) -> None:
        """Grey out what is inside, leaving the box itself foldable.

        The contents are disabled as one widget rather than field by field.
        Qt re-enables children along with their parent unless they were
        disabled in their own right, in which case they would stay dead once
        the parent came back.
        """
        self._content.setEnabled(enabled)

    def _fold(self, expanded: bool) -> None:
        self._content.setVisible(expanded)
        self._update_arrow()

    def _update_arrow(self) -> None:
        self._header.setArrowType(
            Qt.ArrowType.DownArrow
            if self._header.isChecked()
            else Qt.ArrowType.RightArrow
        )


class ActionPanel(QWidget):
    """Where the student types a new vector, and edits the active one."""

    def __init__(self, store: VectorStore) -> None:
        super().__init__()
        self._store = store

        # What the edit fields were last filled from, so `should_refill` can
        # tell a change that matters from one that does not.
        self._shown: tuple[str, Point] | None = None

        layout = QVBoxLayout(self)
        # The reason the edit box is disabled sits outside it. Disabling a
        # widget greys its children, so a hint kept inside would be dimmed
        # exactly when it most needs reading.
        self._edit_hint = QLabel()
        self._edit_hint.setWordWrap(True)
        self._edit_hint.setStyleSheet(f"color: {theme.MUTED_TEXT};")

        layout.addWidget(self._build_create_box())
        layout.addWidget(self._build_edit_box())
        layout.addWidget(self._edit_hint)
        layout.addWidget(self._build_operations())
        layout.addWidget(self._build_settings())

        self._clear = QPushButton("Clear all")
        self._clear.setToolTip("Remove every vector from the scene")
        self._clear.clicked.connect(self._on_clear_all)
        layout.addWidget(self._clear)

        # No trailing stretch: the panel asks for exactly the height its
        # forms need, and the vector list below it takes everything else.
        # Folding a box therefore hands its space straight to the list.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        self.refresh()

    def _build_create_box(self) -> QWidget:
        box = CollapsibleBox("New vector")
        self._create_form = VectorForm("Create", self._on_create)
        box.add(self._create_form)
        return box

    def _build_edit_box(self) -> QWidget:
        self._edit_box = CollapsibleBox("Edit vector")
        self._edit_form = VectorForm("Apply", self._on_apply)
        self._edit_box.add(self._edit_form)
        return self._edit_box

    def _build_operations(self) -> QWidget:
        """The operations over several vectors. Subtraction and scaling join
        this box at G3.4 and G3.5."""
        box = CollapsibleBox("Operations")

        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.GAP_SMALL)

        self._resultant = QPushButton("Resultant")
        self._resultant.setToolTip("Add the ticked vectors and show their sum")
        self._resultant.clicked.connect(self._on_resultant)
        layout.addWidget(self._resultant)

        self._resultant_hint = QLabel(RESULTANT_HINT)
        self._resultant_hint.setWordWrap(True)
        self._resultant_hint.setStyleSheet(f"color: {theme.MUTED_TEXT};")
        layout.addWidget(self._resultant_hint)

        self._resultant_message = QLabel()
        self._resultant_message.setWordWrap(True)
        self._resultant_message.setStyleSheet(ERROR_STYLE)
        self._resultant_message.hide()
        layout.addWidget(self._resultant_message)

        # --- Subtraction (F-16) ---
        # Two dropdowns reading "[ A ] - [ B ]" across one row, with the
        # button beside them. Picking the same vector twice is allowed: the
        # answer is the zero vector and the card says so.
        row = QHBoxLayout()
        row.setSpacing(theme.GAP_SMALL)
        self._minuend = QComboBox()
        self._subtrahend = QComboBox()
        for dropdown in (self._minuend, self._subtrahend):
            dropdown.setMinimumWidth(FIELD_MIN_WIDTH)
        row.addWidget(self._minuend, 1)
        row.addWidget(QLabel(MINUS))
        row.addWidget(self._subtrahend, 1)
        layout.addLayout(row)

        self._subtract = QPushButton("Subtract")
        self._subtract.setToolTip("Show the difference between these two vectors")
        self._subtract.clicked.connect(self._on_subtract)
        layout.addWidget(self._subtract)

        self._subtract_hint = QLabel(SUBTRACT_HINT)
        self._subtract_hint.setWordWrap(True)
        self._subtract_hint.setStyleSheet(f"color: {theme.MUTED_TEXT};")
        layout.addWidget(self._subtract_hint)

        self._subtract_message = QLabel()
        self._subtract_message.setWordWrap(True)
        self._subtract_message.setStyleSheet(ERROR_STYLE)
        self._subtract_message.hide()
        layout.addWidget(self._subtract_message)

        box.add(holder)
        return box


    def _build_settings(self) -> QWidget:
        """Snapping and magnitude sensitivity (F-20, spec section 8).

        Folded at launch, since they are rarely changed. They start at the
        spec's defaults every time; nothing is saved between launches.
        """
        box = CollapsibleBox("Gesture settings", expanded=False)

        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(theme.GAP_SMALL)

        self._snapping = QCheckBox("Snap to axes and planes while steering")
        self._snapping.setChecked(self._store.settings.snapping)
        self._snapping.toggled.connect(self._on_snapping)
        layout.addWidget(self._snapping)

        layout.addWidget(QLabel("Magnitude sensitivity"))
        row = QHBoxLayout()
        # The slider counts steps of 5, so it can only ever produce a value
        # the spec allows: 1 to 10 steps is 5 to 50 units.
        self._sensitivity = QSlider(Qt.Orientation.Horizontal)
        self._sensitivity.setRange(
            config.MAGNITUDE_SENSITIVITY_MIN // config.MAGNITUDE_SENSITIVITY_STEP,
            config.MAGNITUDE_SENSITIVITY_MAX // config.MAGNITUDE_SENSITIVITY_STEP,
        )
        self._sensitivity.setPageStep(1)
        self._sensitivity.setValue(
            self._store.settings.sensitivity // config.MAGNITUDE_SENSITIVITY_STEP
        )
        self._sensitivity.setToolTip(
            "How long a vector one full stretch of the hands makes, when creating "
            "or resizing. Lower for fine control of short vectors."
        )
        self._sensitivity.valueChanged.connect(self._on_sensitivity)
        row.addWidget(self._sensitivity)
        self._sensitivity_value = QLabel()
        row.addWidget(self._sensitivity_value)
        layout.addLayout(row)
        self._show_sensitivity()

        box.add(holder)
        return box

    def _on_snapping(self, on: bool) -> None:
        actions.set_snapping(self._store, on)

    def _on_sensitivity(self, steps: int) -> None:
        actions.set_sensitivity(self._store, steps * config.MAGNITUDE_SENSITIVITY_STEP)
        self._show_sensitivity()

    def _show_sensitivity(self) -> None:
        self._sensitivity_value.setText(
            f"{self._store.settings.sensitivity} units per full stretch"
        )
    def _on_subtract(self) -> None:
        """Show the difference between the two chosen vectors (F-16)."""
        minuend = self._minuend.currentText()
        subtrahend = self._subtrahend.currentText()
        if not minuend or not subtrahend:
            return

        try:
            actions.compute_difference(self._store, minuend, subtrahend)
        except KeyError:
            # A vector was deleted between the list being built and the
            # button being pressed. The refresh will rebuild the dropdowns.
            return
        except ValueError:
            self._subtract_message.setText(
                f"{minuend} {MINUS} {subtrahend} is too large to show."
            )
            self._subtract_message.show()
            return

        self._subtract_message.hide()

    def _fill_dropdowns(self) -> None:
        """Rebuild both vector lists to match the store.

        Rebuilt rather than patched, like the info panel's cards: at most ten
        entries, so working out what changed costs more than starting again,
        and a rebuilt list cannot drift out of step with the store. The
        current choice is kept when that vector is still there, so a refresh
        caused by something unrelated does not move the student's selection.
        """
        names = self._store.names
        for dropdown in (self._minuend, self._subtrahend):
            chosen = dropdown.currentText()
            dropdown.blockSignals(True)
            dropdown.clear()
            dropdown.addItems(names)
            if chosen in names:
                dropdown.setCurrentText(chosen)
            dropdown.blockSignals(False)

    def _on_resultant(self) -> None:
        """Add up the ticked vectors (F-15).

        A sum too large to be a number is refused by `core/operations.py`
        rather than drawn as an infinity, and the student is told which
        expression could not be worked out.
        """
        names = self._store.selected
        try:
            actions.compute_resultant(self._store)
        except ValueError:
            self._resultant_message.setText(
                f"{' + '.join(names)} is too large to show."
            )
            self._resultant_message.show()
            return

        self._resultant_message.hide()

    def refresh(self) -> None:
        """Bring the panel back in step with the store.

        Called by the window when anything changes, the same way the info
        panel and the 3D view are. Every part of the window is told by the
        one place that listens, rather than each subscribing for itself.

        Clear all is disabled while the scene is empty, so the prompt can
        never be raised with nothing to remove.
        """
        self._clear.setEnabled(self._store.count > 0)

        # Two ticks is the rule (F-15), and the hint below the button says so
        # for as long as it is not met.
        enough = len(self._store.selected) >= actions.MIN_FOR_RESULTANT
        self._resultant.setEnabled(enough)
        self._resultant_hint.setVisible(not enough)
        if enough:
            self._resultant_message.hide()

        # Subtraction needs one vector, not two: A - A is allowed (F-16).
        self._fill_dropdowns()
        has_vectors = self._store.count > 0
        self._subtract.setEnabled(has_vectors)
        self._minuend.setEnabled(has_vectors)
        self._subtrahend.setEnabled(has_vectors)
        self._subtract_hint.setVisible(not has_vectors)
        if has_vectors:
            self._subtract_message.hide()

        active = self._store.active
        if should_refill(self._shown, active):
            self._fill_edit(active)

        self._edit_box.set_title(
            "Edit vector" if active is None else f"Edit vector {active.name}"
        )

        # The contents are disabled, not the box, so a locked vector's form
        # can still be folded away.
        editable = active is not None and not active.locked
        self._edit_box.set_content_enabled(editable)
        self._edit_hint.setVisible(not editable)
        if active is None:
            self._edit_hint.setText(NO_VECTOR_HINT)
        elif active.locked:
            self._edit_hint.setText(LOCKED_HINT.format(name=active.name))

    def _fill_edit(self, active: Vector | None) -> None:
        if active is None:
            self._edit_form.clear()
            self._shown = None
            return

        self._edit_form.fill(active.components)
        self._shown = (active.name, active.components)

    def _on_clear_all(self) -> None:
        if confirm_clear_all(self, self._store.count):
            actions.clear_all(self._store)
            self._create_form.clear_message()

    def _on_create(self) -> None:
        parsed = self._create_form.parsed()
        if parsed.error is not None:
            self._create_form.show_message(parsed.error)
            return

        vector = actions.create_vector(self._store, parsed.components)
        if vector is None:
            self._create_form.show_message(LIMIT_TEXT)
            return

        self._create_form.clear_message()

    def _on_apply(self) -> None:
        """Apply the edit form to the active vector (F-08).

        The lock is checked again by `actions.edit_vector`. The box is
        disabled for a locked vector, so this should not be reachable, but
        Enter can arrive in a field the instant before a refresh does.
        """
        active = self._store.active
        if active is None:
            return

        parsed = self._edit_form.parsed()
        if parsed.error is not None:
            self._edit_form.show_message(parsed.error)
            return

        if not actions.edit_vector(self._store, active.name, parsed.components):
            self._edit_form.show_message(f"Vector {active.name} is locked.")
            return

        self._edit_form.clear_message()


def _field_row(fields: dict[str, QLineEdit], *, hint: str | None = None) -> QWidget:
    """One set of labelled input boxes, side by side on a single row.

    Stacked rows were costing height the info panel needed: the two forms
    took 498px of an 800px window between them, leaving room for two of the
    ten vector cards. Three fields on one row give back about 64px per form,
    and a typed number is short enough not to need a wide box.
    """
    widget = QWidget()
    outer = QVBoxLayout(widget)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(2)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(theme.GAP_SMALL)
    for label, field in fields.items():
        field.setMinimumWidth(FIELD_MIN_WIDTH)
        row.addWidget(QLabel(label))
        row.addWidget(field, 1)
    outer.addLayout(row)

    if hint is not None:
        text = QLabel(hint)
        text.setWordWrap(True)
        text.setStyleSheet(f"color: {theme.MUTED_TEXT};")
        outer.addWidget(text)

    return widget


def _angle_rows(length: QLineEdit, angles: tuple[QLineEdit, ...]) -> QWidget:
    """The magnitude with the hint beside it, then alpha, beta, gamma.

    Four fields do not fit one row of the 300 px panel: at widths that did,
    an angle such as 131.81 lost its first digit. Two rows are the same
    height as the components mode's row plus its hint line, so the form
    grows no taller than the old r, theta, phi form did.
    """
    widget = QWidget()
    outer = QVBoxLayout(widget)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(2)

    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(theme.GAP_SMALL)
    length.setMinimumWidth(FIELD_MIN_WIDTH)
    top.addWidget(QLabel("|v|"))
    top.addWidget(length, 1)
    hint = QLabel(ANGLE_HINT)
    hint.setStyleSheet(f"color: {theme.MUTED_TEXT};")
    top.addWidget(hint)
    outer.addLayout(top)

    outer.addWidget(_field_row(dict(zip(ANGLE_NAMES, angles))))
    return widget

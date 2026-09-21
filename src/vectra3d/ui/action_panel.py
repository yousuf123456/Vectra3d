"""The action panel: typing exact vectors (F-04).

A vector can be entered either as components (x, y, z) or as a magnitude and
two angles, chosen with a toggle. The two are separate ways of saying the same
thing; the toggle switches which fields are shown and does not convert what is
already typed. Converting between them is F-08's job in G2.4.

Input is checked when **Create** is pressed rather than keystroke by
keystroke, so someone who types `3,5` is told what is wrong instead of having
the comma silently refused.

The parsing and checking are module-level functions, separate from the
widgets, so they can be tested without building a window.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from vectra3d.core.spherical import THETA_MAX, THETA_MIN, to_components
from vectra3d.state import actions, naming
from vectra3d.state.store import VectorStore
from vectra3d.ui.dialogs import confirm_clear_all

ERROR_STYLE = "color: #C2185B;"


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
    if math.isinf(value):
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


def parse_angles(r: str, theta: str, phi: str) -> Parsed:
    """Read the magnitude and angles form.

    Phi is normalized rather than rejected, because
    `interaction-spec.md` section 2.3 defines any value as meaningful once
    brought into 0 to 360 degrees. Theta is rejected outside 0 to 180,
    because outside that range it is not defined at all.
    """
    values: list[float] = []
    for text, name in ((r, "the magnitude"), (theta, "θ"), (phi, "φ")):
        value, error = parse_number(text, name)
        if error is not None:
            return Parsed(error=error)
        values.append(value)

    magnitude, theta_deg, phi_deg = values
    if magnitude <= 0:
        return Parsed(error="The magnitude must be greater than 0.")
    if not THETA_MIN <= theta_deg <= THETA_MAX:
        return Parsed(error="θ must be between 0° and 180°.")

    return Parsed(components=to_components(magnitude, theta_deg, phi_deg))


class ActionPanel(QWidget):
    """Where the student types a vector and presses Create."""

    def __init__(self, store: VectorStore) -> None:
        super().__init__()
        self._store = store

        layout = QVBoxLayout(self)
        layout.addWidget(self._build_form())

        self._clear = QPushButton("Clear all")
        self._clear.setToolTip("Remove every vector from the scene")
        self._clear.clicked.connect(self._on_clear_all)
        layout.addWidget(self._clear)
        layout.addStretch()

        self.refresh()

    def _build_form(self) -> QWidget:
        box = QGroupBox("New vector")
        layout = QVBoxLayout(box)

        self._by_components = QRadioButton("Components (x, y, z)")
        self._by_angles = QRadioButton("Magnitude + angles")
        self._by_components.setChecked(True)

        mode = QButtonGroup(self)
        mode.addButton(self._by_components, 0)
        mode.addButton(self._by_angles, 1)
        layout.addWidget(self._by_components)
        layout.addWidget(self._by_angles)

        self._fields = QStackedWidget()
        self._x, self._y, self._z = QLineEdit(), QLineEdit(), QLineEdit()
        self._r, self._theta, self._phi = QLineEdit(), QLineEdit(), QLineEdit()
        self._fields.addWidget(_form({"x": self._x, "y": self._y, "z": self._z}))
        self._fields.addWidget(
            _form({"r": self._r, "θ (from +z)": self._theta, "φ (from +x)": self._phi})
        )
        mode.idToggled.connect(self._on_mode_changed)
        layout.addWidget(self._fields)

        create = QPushButton("Create")
        create.clicked.connect(self._on_create)
        layout.addWidget(create)

        self._message = QLabel()
        self._message.setWordWrap(True)
        self._message.setStyleSheet(ERROR_STYLE)
        layout.addWidget(self._message)

        return box

    def refresh(self) -> None:
        """Bring the panel back in step with the store.

        Called by the window when anything changes, the same way the info
        panel and the 3D view are. Every part of the window is told by the
        one place that listens, rather than each subscribing for itself.

        Clear all is disabled while the scene is empty, so the prompt can
        never be raised with nothing to remove.
        """
        self._clear.setEnabled(self._store.count > 0)

    def _on_clear_all(self) -> None:
        if confirm_clear_all(self, self._store.count):
            actions.clear_all(self._store)
            self._message.clear()

    def _on_mode_changed(self, index: int, checked: bool) -> None:
        if checked:
            self._fields.setCurrentIndex(index)
            self._message.clear()

    def _on_create(self) -> None:
        if self._by_components.isChecked():
            parsed = parse_components(
                self._x.text(), self._y.text(), self._z.text()
            )
        else:
            parsed = parse_angles(
                self._r.text(), self._theta.text(), self._phi.text()
            )

        if parsed.error is not None:
            self._message.setText(parsed.error)
            return

        vector = actions.create_vector(self._store, parsed.components)
        if vector is None:
            self._message.setText(
                f"The scene already has the most vectors allowed "
                f"({naming.MAX_VECTORS}). Delete one to make room."
            )
            return

        self._message.clear()


def _form(fields: dict[str, QLineEdit]) -> QWidget:
    """One set of labelled input boxes."""
    widget = QWidget()
    layout = QFormLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    for label, field in fields.items():
        layout.addRow(label, field)
    return widget

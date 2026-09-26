"""The Gesture settings box, pressed like a student would (F-20).

The widgets are driven for real: a control wired to nothing fails silently,
because Qt swallows exceptions raised in slots (see `test_result_card.py`).
"""

from __future__ import annotations

import pytest

from vectra3d.state.store import VectorStore

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.ui.action_panel import ActionPanel  # noqa: E402


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


@pytest.fixture
def panel(app: QApplication):
    panel = ActionPanel(VectorStore())
    panel.show()
    yield panel
    panel.close()


def test_the_box_starts_folded_at_the_defaults(panel) -> None:
    assert not panel._snapping.isVisible()
    assert panel._snapping.isChecked()
    assert panel._sensitivity.value() * 5 == 25
    assert panel._sensitivity_value.text() == "25 units per full stretch"


def test_the_checkbox_turns_snapping_off_and_on(panel) -> None:
    panel._snapping.click()
    assert not panel._store.settings.snapping
    panel._snapping.click()
    assert panel._store.settings.snapping


def test_the_slider_sets_the_sensitivity_in_steps_of_5(panel) -> None:
    panel._sensitivity.setValue(10)
    assert panel._store.settings.sensitivity == 50
    assert panel._sensitivity_value.text() == "50 units per full stretch"
    panel._sensitivity.setValue(1)
    assert panel._store.settings.sensitivity == 5


def test_the_slider_cannot_go_past_the_range(panel) -> None:
    panel._sensitivity.setValue(99)
    assert panel._store.settings.sensitivity == 50
    panel._sensitivity.setValue(0)
    assert panel._store.settings.sensitivity == 5

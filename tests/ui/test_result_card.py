"""The result card's buttons actually do something when pressed.

These open a real `QApplication`, against the convention followed since G2.2
that panel logic is lifted into plain functions and tested without one. That
convention earns its keep where a widget holds no rules of its own - but it
cannot see a button wired to nothing, and that is exactly what went wrong
here.

**Show how** was connected to a method that called its Qt signal instead of
emitting it (`self.show_how_requested()` rather than `.emit()`). PySide6
raises `TypeError: native Qt signal instance is not callable`, Qt swallowed
the exception inside the slot, and the button silently did nothing while the
suite stayed green and an off-screen run of the animation passed - because
that run called the window's method directly and never pressed the button.

So these tests press the buttons.
"""

from __future__ import annotations

import pytest

from vectra3d.state import actions
from vectra3d.state.store import VectorStore

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication, QToolButton  # noqa: E402

from vectra3d.ui.info_panel import SAVE_TEXT, SHOW_TEXT, InfoPanel  # noqa: E402


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def store_with_result() -> VectorStore:
    store = VectorStore()
    actions.create_vector(store, (3.0, 1.0, 0.0))
    actions.create_vector(store, (1.0, 4.0, 2.0))
    actions.toggle_selected(store, "A")
    actions.toggle_selected(store, "B")
    actions.compute_resultant(store)
    return store


def panel_for(store: VectorStore) -> InfoPanel:
    panel = InfoPanel(store)
    panel.refresh(
        store.vectors,
        store.active_name,
        store.selected,
        None,
        None,
        store.result,
        store.result_error,
    )
    # Cards are rebuilt on every refresh and the replaced widgets linger until
    # deferred deletion runs, so without this `findChildren` returns stale
    # ones from the previous build.
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    return panel


def button_labelled(panel: InfoPanel, text: str) -> QToolButton:
    for button in panel.findChildren(QToolButton):
        if button.text() == text:
            return button
    raise AssertionError(f"no button labelled {text!r} on the panel")


def test_the_result_card_offers_show_how(app: QApplication) -> None:
    panel = panel_for(store_with_result())
    assert button_labelled(panel, SHOW_TEXT).isEnabled()


def test_pressing_show_how_raises_the_request(app: QApplication) -> None:
    # The regression test. Before the fix this passed through a slot that
    # raised TypeError, so nothing ever reached the window.
    panel = panel_for(store_with_result())
    asked: list[bool] = []
    panel.show_how_requested.connect(lambda: asked.append(True))

    button_labelled(panel, SHOW_TEXT).click()

    assert asked == [True]


def test_pressing_save_as_vector_saves_it(app: QApplication) -> None:
    # The other button on the card, checked the same way rather than trusting
    # that one working button means both do.
    store = store_with_result()
    panel = panel_for(store)

    button_labelled(panel, SAVE_TEXT).click()

    assert store.count == 3
    assert store.get("C") is not None
    assert store.result is None


def test_no_result_means_no_result_buttons(app: QApplication) -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    panel = panel_for(store)

    labels = {button.text() for button in panel.findChildren(QToolButton)}
    assert SHOW_TEXT not in labels
    assert SAVE_TEXT not in labels


# --- Subtraction (F-16) ---


def test_pressing_subtract_makes_a_difference(app: QApplication) -> None:
    # A button test, not a logic test: `compute_difference` is covered in
    # tests/state/test_result.py. What this checks is that the panel's
    # dropdowns and button are actually wired to it - the class of fault that
    # G3.3's Show how button had, which every other kind of test missed.
    from vectra3d.ui.action_panel import ActionPanel

    store = VectorStore()
    actions.create_vector(store, (5.0, 7.0, 9.0))
    actions.create_vector(store, (1.0, 2.0, 3.0))

    panel = ActionPanel(store)
    panel.refresh()
    panel._minuend.setCurrentText("A")
    panel._subtrahend.setCurrentText("B")
    panel._subtract.click()

    assert store.result is not None
    assert store.result.components == (4.0, 5.0, 6.0)
    assert store.result.sources == ("A", "B")


def test_the_dropdowns_follow_the_vectors_in_the_scene(app: QApplication) -> None:
    from vectra3d.ui.action_panel import ActionPanel

    store = VectorStore()
    panel = ActionPanel(store)
    assert panel._minuend.count() == 0
    assert not panel._subtract.isEnabled()

    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.create_vector(store, (2.0, 0.0, 0.0))
    panel.refresh()

    assert [panel._minuend.itemText(i) for i in range(panel._minuend.count())] == [
        "A",
        "B",
    ]
    assert panel._subtract.isEnabled()

    actions.delete_vector(store, "A")
    panel.refresh()

    assert [panel._minuend.itemText(i) for i in range(panel._minuend.count())] == ["B"]


def test_a_refresh_keeps_the_students_choice(app: QApplication) -> None:
    # Every action notifies every listener, so an unrelated change refreshes
    # this panel too. It must not quietly move the selection back to A.
    from vectra3d.ui.action_panel import ActionPanel

    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.create_vector(store, (2.0, 0.0, 0.0))
    actions.create_vector(store, (3.0, 0.0, 0.0))

    panel = ActionPanel(store)
    panel.refresh()
    panel._subtrahend.setCurrentText("C")

    actions.set_active(store, "B")
    panel.refresh()

    assert panel._subtrahend.currentText() == "C"


def test_the_same_vector_twice_is_allowed_and_noted(app: QApplication) -> None:
    # F-16 allows it on purpose, and the card explains the dashes it causes.
    from vectra3d.ui.action_panel import ActionPanel
    from vectra3d.ui.info_panel import note_for

    store = VectorStore()
    actions.create_vector(store, (2.0, 3.0, 4.0))

    panel = ActionPanel(store)
    panel.refresh()
    panel._minuend.setCurrentText("A")
    panel._subtrahend.setCurrentText("A")
    panel._subtract.click()

    assert store.result is not None
    assert store.result.components == (0.0, 0.0, 0.0)
    assert note_for(store.result.components) is not None

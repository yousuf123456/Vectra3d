"""The forms' scroll area asks for what its contents need, and no minimum.

Found at G4.1: without it the forms set the window's minimum height to 830px,
taller than the 728px a 1366x768 laptop has free, and the window grew off the
bottom of the screen the first time the camera picture arrived.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget  # noqa: E402

from vectra3d.ui.fitted_scroll_area import FittedScrollArea  # noqa: E402

CONTENT_HEIGHT = 700


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def tall_content() -> tuple[QWidget, QWidget]:
    content = QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(0, 0, 0, 0)
    part = QWidget()
    part.setFixedHeight(CONTENT_HEIGHT)
    layout.addWidget(part)
    return content, part


def test_asks_for_its_contents_full_height(app: QApplication) -> None:
    content, _ = tall_content()

    area = FittedScrollArea(content)

    assert area.sizeHint().height() == CONTENT_HEIGHT


def test_sets_no_minimum_height_so_it_can_never_push_the_window_off_screen(
    app: QApplication,
) -> None:
    content, _ = tall_content()

    area = FittedScrollArea(content)

    assert area.minimumSizeHint().height() == 0
    assert area.minimumSizeHint().width() >= content.minimumSizeHint().width()


def test_folding_part_of_the_contents_is_noticed(app: QApplication) -> None:
    # A folded box must free its space, or folding does nothing - the fault
    # the old panel splitter had.
    # Checked through a real layout, as in the window: what matters is the
    # height the layout hands out, which it caches until told to ask again.
    content, part = tall_content()
    column = QWidget()
    layout = QVBoxLayout(column)
    area = FittedScrollArea(content)
    layout.addWidget(area)
    layout.addStretch(1)
    column.resize(300, CONTENT_HEIGHT + 200)
    column.show()
    app.processEvents()
    assert area.height() >= CONTENT_HEIGHT

    part.hide()
    for _ in range(5):
        app.processEvents()

    assert area.height() < CONTENT_HEIGHT
    column.close()

"""Proves the bundled app icon is present and loads at the sizes Windows uses.

An icon Qt cannot read fails silently: the window just shows no icon. So this
loads it the way `app.main()` does, through `resource_path()`, and checks the
sizes the title bar, the taskbar and the Explorer file view pick from.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QSize  # noqa: E402
from PySide6.QtGui import QIcon  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from vectra3d.paths import APP_ICON, resource_path  # noqa: E402


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_icon_file_is_bundled() -> None:
    icon = resource_path(APP_ICON)

    assert icon.is_file(), f"app icon missing at {icon}"


def test_icon_loads_at_every_size_windows_uses(app: QApplication) -> None:
    icon = QIcon(str(resource_path(APP_ICON)))

    assert not icon.isNull()
    sizes = set(icon.availableSizes())
    for side in (16, 32, 48, 256):
        assert QSize(side, side) in sizes

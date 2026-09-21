"""The look of the application: one palette, applied in one place.

The panels are themed by `qdarktheme`, which sets an application-wide
stylesheet and palette. That only works if the rest of the app agrees with it.
Before this module the info panel carried its own hardcoded greys and blues,
chosen against Qt's default look; under a theme they would read as a patch of
a different design.

So the colours the app picks for itself live here, beside the theme call that
sets everything else, and they are chosen to sit inside `qdarktheme`'s light
palette rather than beside it. Anything that needs one imports it from here.

The theme is light rather than dark, and deliberately. `project-overview.md`
describes a teacher projecting the app in a lecture, where a dark background
washes out badly, and the ten vector colours were judged and approved against
a light scene over three rounds in G1.3.
"""

from __future__ import annotations

import qdarktheme
from PySide6.QtWidgets import QApplication

THEME = "light"

# The 3D view's background, a shade off the panel background so the scene
# reads as a distinct surface rather than the window continuing into it.
SCENE_BACKGROUND = "#F7F8FA"

# The active vector's card: a tint and a stronger border, matching the halo
# its arrow carries in the 3D view.
ACTIVE_BACKGROUND = "#E4EDF7"
ACTIVE_BORDER = "#5B8DBE"

# A resting card. Low contrast on purpose: with up to ten of them stacked in a
# narrow column, strong outlines turn the panel into a grid of boxes.
CARD_BACKGROUND = "#FFFFFF"
CARD_BORDER = "#E1E4E8"

# Secondary text: axis letters, hints, the empty-list message.
MUTED_TEXT = "#6B7280"

# Spacing, so padding is consistent across the panels instead of each widget
# inventing its own.
GAP_SMALL = 6
GAP = 10
GAP_LARGE = 16

CARD_RADIUS = 6

# Rules `qdarktheme` does not cover, because they are about this app's own
# widgets rather than about Qt's. Kept small: the theme does the heavy work.
EXTRA_RULES = f"""
QLabel[role="title"] {{
    font-size: 13px;
    font-weight: 600;
    padding-bottom: {GAP_SMALL}px;
}}
QLabel[role="muted"] {{
    color: {MUTED_TEXT};
}}
QToolBar {{
    padding: {GAP_SMALL}px;
    spacing: {GAP_SMALL}px;
    border: none;
}}
"""


def apply(app: QApplication) -> None:
    """Theme the whole application. Called once, before the window is built."""
    qdarktheme.setup_theme(THEME, additional_qss=EXTRA_RULES)

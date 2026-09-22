"""Dialogs that ask before something irreversible happens.

The message text is built by a separate function from the dialog that shows
it, so what the student is told can be tested without a window appearing.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget


def clear_all_message(count: int) -> str:
    """What the Clear all prompt says.

    It names the number going and says that locked vectors go too (F-10).

    It used to end "It cannot be undone", which stopped being true at G2.8
    when undo arrived. A prompt that overstates what is at stake teaches
    students to ignore prompts, so the sentence was removed rather than
    softened.
    """
    vectors = "vector" if count == 1 else "vectors"
    return (
        f"Remove all {count} {vectors}?\n\n"
        "This removes every vector, including any that are locked."
    )


def confirm_clear_all(parent: QWidget, count: int) -> bool:
    """Ask before clearing the scene. True if the student agreed."""
    box = QMessageBox(parent)
    box.setWindowTitle("Clear all")
    box.setIcon(QMessageBox.Icon.Warning)
    box.setText(clear_all_message(count))
    remove = box.addButton("Remove all", QMessageBox.ButtonRole.DestructiveRole)
    box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
    # Cancel is the default, so that a stray Enter keeps the vectors.
    box.setDefaultButton(QMessageBox.StandardButton.Cancel)

    box.exec()
    return box.clickedButton() is remove

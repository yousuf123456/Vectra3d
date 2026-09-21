"""Dialogs that ask before something irreversible happens.

The message text is built by a separate function from the dialog that shows
it, so what the student is told can be tested without a window appearing.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget


def clear_all_message(count: int) -> str:
    """What the Clear all prompt says.

    It names the number going, says that locked vectors go too (F-10), and
    warns that it cannot be undone. Locking itself arrives in G2.5; the
    sentence is written now because the criterion requires it and because
    the wording will still be right then.
    """
    vectors = "vector" if count == 1 else "vectors"
    return (
        f"Remove all {count} {vectors}?\n\n"
        "This removes every vector, including any that are locked. "
        "It cannot be undone."
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

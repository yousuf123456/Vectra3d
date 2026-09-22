"""What the Clear all prompt tells the student (F-10)."""

from __future__ import annotations

import pytest

from vectra3d.ui.dialogs import clear_all_message


def test_the_message_names_how_many_will_go() -> None:
    assert "all 4 vectors" in clear_all_message(4)


def test_one_vector_reads_as_singular() -> None:
    assert "all 1 vector?" in clear_all_message(1)
    assert "vectors" not in clear_all_message(1)


@pytest.mark.parametrize("count", [1, 2, 10])
def test_the_message_says_locked_vectors_go_too(count: int) -> None:
    # F-10 requires this explicitly.
    assert "including any that are locked" in clear_all_message(count)


@pytest.mark.parametrize("count", [1, 2, 10])
def test_the_message_no_longer_claims_it_cannot_be_undone(count: int) -> None:
    # It said so until G2.8, and undo made it untrue. A prompt that
    # overstates what is at stake teaches students to ignore prompts, so the
    # sentence went rather than being softened. This test replaces the one
    # that asserted the old wording, which is what caught the change.
    assert "cannot be undone" not in clear_all_message(count)

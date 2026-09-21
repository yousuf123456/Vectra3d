"""Ticking vectors for an operation, and keeping it apart from the active one.

F-05a asks for two independent things: exactly one active vector, and a
separate set of vectors ticked for the resultant. These tests hold that line,
because the two are easy to entangle by accident.
"""

from __future__ import annotations

import pytest

from vectra3d.state import actions
from vectra3d.state.store import VectorStore


@pytest.fixture
def store() -> VectorStore:
    """Three vectors, A B C, with A active as the first one created."""
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.create_vector(store, (0.0, 1.0, 0.0))
    actions.create_vector(store, (0.0, 0.0, 1.0))
    actions.set_active(store, "A")
    return store


class TestTicking:
    def test_nothing_is_ticked_to_begin_with(self, store: VectorStore) -> None:
        assert store.selected == ()

    def test_a_vector_can_be_ticked(self, store: VectorStore) -> None:
        assert actions.toggle_selected(store, "B") is True
        assert store.selected == ("B",)
        assert store.is_selected("B")

    def test_ticking_again_unticks(self, store: VectorStore) -> None:
        actions.toggle_selected(store, "B")
        assert actions.toggle_selected(store, "B") is False
        assert store.selected == ()

    def test_several_vectors_can_be_ticked_at_once(self, store: VectorStore) -> None:
        actions.toggle_selected(store, "C")
        actions.toggle_selected(store, "A")
        # Name order, not the order they were ticked in, so the panel and any
        # operation read them in the order the student sees them.
        assert store.selected == ("A", "C")

    def test_ticking_an_unknown_vector_is_refused(self, store: VectorStore) -> None:
        with pytest.raises(KeyError):
            actions.toggle_selected(store, "Z")

    def test_clear_selection_unticks_everything_but_keeps_the_vectors(
        self, store: VectorStore
    ) -> None:
        actions.toggle_selected(store, "A")
        actions.toggle_selected(store, "B")
        actions.clear_selection(store)
        assert store.selected == ()
        assert store.names == ("A", "B", "C")

    def test_every_change_notifies_once(self, store: VectorStore) -> None:
        calls: list[int] = []
        store.subscribe(lambda: calls.append(1))
        actions.toggle_selected(store, "A")
        actions.clear_selection(store)
        assert len(calls) == 2


class TestIndependentFromTheActiveVector:
    def test_ticking_does_not_change_which_vector_is_active(
        self, store: VectorStore
    ) -> None:
        actions.toggle_selected(store, "C")
        assert store.active_name == "A"

    def test_activating_does_not_tick(self, store: VectorStore) -> None:
        actions.set_active(store, "B")
        assert store.selected == ()

    def test_activating_does_not_disturb_existing_ticks(
        self, store: VectorStore
    ) -> None:
        actions.toggle_selected(store, "A")
        actions.toggle_selected(store, "C")
        actions.set_active(store, "B")
        assert store.selected == ("A", "C")
        assert store.active_name == "B"

    def test_the_active_vector_can_itself_be_ticked(self, store: VectorStore) -> None:
        # Nothing stops it; the two marks simply mean different things.
        actions.toggle_selected(store, "A")
        assert store.active_name == "A"
        assert store.is_selected("A")


class TestTicksSurviveUnrelatedChanges:
    def test_creating_another_vector_keeps_the_ticks(
        self, store: VectorStore
    ) -> None:
        actions.toggle_selected(store, "B")
        actions.create_vector(store, (5.0, 5.0, 5.0))
        assert store.selected == ("B",)

    def test_deleting_a_different_vector_keeps_the_ticks(
        self, store: VectorStore
    ) -> None:
        actions.toggle_selected(store, "B")
        actions.delete_vector(store, "C")
        assert store.selected == ("B",)


class TestPruning:
    def test_deleting_a_ticked_vector_drops_its_tick(
        self, store: VectorStore
    ) -> None:
        actions.toggle_selected(store, "B")
        actions.delete_vector(store, "B")
        assert store.selected == ()

    def test_clear_all_drops_every_tick(self, store: VectorStore) -> None:
        actions.toggle_selected(store, "A")
        actions.toggle_selected(store, "B")
        actions.clear_all(store)
        assert store.selected == ()

    def test_a_reused_letter_does_not_inherit_the_old_tick(
        self, store: VectorStore
    ) -> None:
        # Names are reused: deleting B means the next vector created is also
        # B. Without pruning, that brand-new vector would appear ticked.
        actions.toggle_selected(store, "B")
        actions.delete_vector(store, "B")
        new = actions.create_vector(store, (9.0, 9.0, 9.0))
        assert new is not None
        assert new.name == "B"
        assert store.is_selected("B") is False
        assert store.selected == ()

    def test_a_reused_letter_after_clear_all_is_not_ticked(
        self, store: VectorStore
    ) -> None:
        actions.toggle_selected(store, "A")
        actions.clear_all(store)
        new = actions.create_vector(store, (1.0, 2.0, 3.0))
        assert new is not None
        assert new.name == "A"
        assert store.is_selected("A") is False


class TestTheSelectionCannotBeChangedFromOutside:
    def test_the_returned_selection_is_a_tuple(self, store: VectorStore) -> None:
        # A set would let a caller tick a vector without going through an
        # action, which is what `architecture.md` section 2 forbids.
        actions.toggle_selected(store, "A")
        assert isinstance(store.selected, tuple)

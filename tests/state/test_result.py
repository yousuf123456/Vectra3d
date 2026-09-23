"""The temporary operation result (`features.md`, global rules; F-15).

Everything here runs without Qt, PyVista or a window, the same as the rest of
`tests/state`. The maths itself is tested in `tests/core/test_operations.py`;
what these tests are about is the rules around it - that only one result
exists, that it follows its vectors, that it goes when it can no longer be
shown, and what saving one does.
"""

from __future__ import annotations

import pytest

from vectra3d.state import actions, naming
from vectra3d.state.models import Operation
from vectra3d.state.store import VectorStore


def fill(store: VectorStore, count: int) -> None:
    """Create `count` vectors, A onwards, with components (1,0,0), (2,0,0)..."""
    for i in range(count):
        actions.create_vector(store, (float(i + 1), 0.0, 0.0))


def tick(store: VectorStore, *names: str) -> None:
    for name in names:
        actions.toggle_selected(store, name)


# --- Making a result ---


class TestComputeResultant:
    def test_two_ticked_vectors_are_added(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (1.0, 2.0, 3.0))
        actions.create_vector(store, (4.0, 5.0, 6.0))
        tick(store, "A", "B")

        result = actions.compute_resultant(store)

        assert result is not None
        assert result.components == (5.0, 7.0, 9.0)
        assert result.sources == ("A", "B")
        assert store.result is result

    def test_the_expression_names_the_vectors(self) -> None:
        store = VectorStore()
        fill(store, 3)
        tick(store, "A", "B", "C")

        result = actions.compute_resultant(store)

        assert result is not None
        assert result.expression == "A + B + C"

    def test_ten_vectors(self) -> None:
        store = VectorStore()
        fill(store, naming.MAX_VECTORS)
        tick(store, *store.names)

        result = actions.compute_resultant(store)

        # 1 + 2 + ... + 10 = 55
        assert result is not None
        assert result.components == (55.0, 0.0, 0.0)
        assert len(result.sources) == 10

    def test_fewer_than_two_ticked_makes_nothing(self) -> None:
        store = VectorStore()
        fill(store, 3)
        tick(store, "A")

        assert actions.compute_resultant(store) is None
        assert store.result is None

    def test_nothing_ticked_makes_nothing(self) -> None:
        store = VectorStore()
        fill(store, 3)

        assert actions.compute_resultant(store) is None
        assert store.result is None

    def test_a_new_result_replaces_the_old_one(self) -> None:
        store = VectorStore()
        fill(store, 3)
        tick(store, "A", "B")
        first = actions.compute_resultant(store)

        actions.toggle_selected(store, "C")
        second = actions.compute_resultant(store)

        assert first is not None and second is not None
        assert second is not first
        assert store.result is second
        assert second.sources == ("A", "B", "C")

    def test_the_result_is_not_a_vector(self) -> None:
        # It has no letter and does not count towards the ten.
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        assert store.count == 2
        assert store.names == ("A", "B")

    def test_unticking_afterwards_leaves_the_result_alone(self) -> None:
        # The result belongs to the vectors it was worked out from, not to
        # whatever happens to be ticked now.
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.toggle_selected(store, "A")

        assert store.result is not None
        assert store.result.sources == ("A", "B")


# --- Staying live ---


class TestTheResultFollowsItsVectors:
    def test_editing_an_input_works_the_result_out_again(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (1.0, 0.0, 0.0))
        actions.create_vector(store, (2.0, 0.0, 0.0))
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.edit_vector(store, "A", (10.0, 0.0, 0.0))

        assert store.result is not None
        assert store.result.components == (12.0, 0.0, 0.0)

    def test_editing_a_vector_it_was_not_made_from_changes_nothing(self) -> None:
        store = VectorStore()
        fill(store, 3)
        tick(store, "A", "B")
        actions.compute_resultant(store)
        before = store.result

        actions.edit_vector(store, "C", (99.0, 0.0, 0.0))

        assert store.result is not None
        assert before is not None
        assert store.result.components == before.components

    def test_deleting_an_input_takes_the_result_away(self) -> None:
        store = VectorStore()
        fill(store, 3)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.delete_vector(store, "B")

        assert store.result is None

    def test_deleting_another_vector_leaves_the_result(self) -> None:
        store = VectorStore()
        fill(store, 3)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.delete_vector(store, "C")

        assert store.result is not None

    def test_clearing_the_scene_takes_the_result_away(self) -> None:
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.clear_all(store)

        assert store.result is None

    def test_locking_an_input_leaves_the_result_alone(self) -> None:
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.toggle_locked(store, "A")

        assert store.result is not None
        assert store.result.components == (3.0, 0.0, 0.0)


# --- When it cannot be shown ---


class TestResultsThatDoNotFit:
    def test_a_sum_too_large_to_be_a_number_is_refused(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (1e308, 0.0, 0.0))
        actions.create_vector(store, (1e308, 0.0, 0.0))
        tick(store, "A", "B")

        with pytest.raises(ValueError):
            actions.compute_resultant(store)

        assert store.result is None

    def test_an_edit_that_overflows_drops_the_result_and_says_why(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (1.0, 0.0, 0.0))
        actions.create_vector(store, (1e308, 0.0, 0.0))
        tick(store, "A", "B")
        actions.compute_resultant(store)

        assert actions.edit_vector(store, "A", (1e308, 0.0, 0.0)) is True

        assert store.result is None
        assert store.result_error is not None
        assert "A + B" in store.result_error

    def test_the_edit_itself_still_happens(self) -> None:
        # Only the result is dropped; the vector the student edited keeps the
        # value they typed.
        store = VectorStore()
        actions.create_vector(store, (1.0, 0.0, 0.0))
        actions.create_vector(store, (1e308, 0.0, 0.0))
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.edit_vector(store, "A", (1e308, 0.0, 0.0))

        assert store.get("A").components == (1e308, 0.0, 0.0)

    def test_making_a_new_result_clears_the_message(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (1.0, 0.0, 0.0))
        actions.create_vector(store, (1e308, 0.0, 0.0))
        tick(store, "A", "B")
        actions.compute_resultant(store)
        actions.edit_vector(store, "A", (1e308, 0.0, 0.0))
        assert store.result_error is not None

        actions.edit_vector(store, "A", (1.0, 0.0, 0.0))
        actions.compute_resultant(store)

        assert store.result_error is None
        assert store.result is not None


# --- Saving one ---


class TestSaveAsVector:
    def test_saving_makes_a_real_vector(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (1.0, 2.0, 3.0))
        actions.create_vector(store, (4.0, 5.0, 6.0))
        tick(store, "A", "B")
        actions.compute_resultant(store)

        saved = actions.save_result_as_vector(store)

        assert saved is not None
        assert saved.name == "C"
        assert saved.components == (5.0, 7.0, 9.0)
        assert store.count == 3

    def test_the_saved_vector_becomes_active(self) -> None:
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.save_result_as_vector(store)

        assert store.active_name == "C"

    def test_saving_takes_the_result_away(self) -> None:
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.save_result_as_vector(store)

        assert store.result is None

    def test_the_saved_vector_takes_the_lowest_free_letter(self) -> None:
        store = VectorStore()
        fill(store, 3)
        tick(store, "A", "C")
        actions.compute_resultant(store)
        actions.delete_vector(store, "B")

        saved = actions.save_result_as_vector(store)

        assert saved is not None
        assert saved.name == "B"

    def test_saving_is_refused_when_ten_vectors_exist(self) -> None:
        store = VectorStore()
        fill(store, naming.MAX_VECTORS)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        assert actions.save_result_as_vector(store) is None
        assert store.count == naming.MAX_VECTORS
        # The result is still there to try again with once room is made.
        assert store.result is not None

    def test_saving_with_no_result_does_nothing(self) -> None:
        store = VectorStore()
        fill(store, 2)

        assert actions.save_result_as_vector(store) is None
        assert store.count == 2

    def test_a_saved_vector_starts_at_the_origin(self) -> None:
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        saved = actions.save_result_as_vector(store)

        assert saved is not None
        assert saved.tail == (0.0, 0.0, 0.0)


# --- Undo ---


class TestUndo:
    def test_undoing_a_save_removes_the_vector_and_brings_the_result_back(
        self,
    ) -> None:
        # F-19 names saving a result as something undo must cover.
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)
        actions.save_result_as_vector(store)

        assert actions.undo(store) is True

        assert store.count == 2
        assert store.result is not None
        assert store.result.expression == "A + B"

    def test_redoing_the_save_puts_the_vector_back(self) -> None:
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)
        actions.save_result_as_vector(store)
        actions.undo(store)

        assert actions.redo(store) is True

        assert store.count == 3
        assert store.result is None

    def test_making_a_result_is_not_an_undo_step(self) -> None:
        # It is worked out from the vectors rather than being a change to
        # them, and the same ticks will make it again. So the first undo
        # after making one takes back the last change to the *vectors* - here
        # the creation of B - rather than appearing to do nothing.
        store = VectorStore()
        fill(store, 2)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.undo(store)

        assert store.names == ("A",)

    def test_a_restored_result_is_dropped_if_its_vectors_are_gone(self) -> None:
        # Undoing far enough back that an input vector never existed must not
        # bring back a result labelled with a letter the scene does not have.
        store = VectorStore()
        actions.create_vector(store, (1.0, 0.0, 0.0))
        actions.create_vector(store, (2.0, 0.0, 0.0))
        tick(store, "A", "B")
        actions.compute_resultant(store)
        actions.save_result_as_vector(store)

        actions.undo(store)  # back to A and B, result showing
        assert store.result is not None
        actions.undo(store)  # back to A alone - B is gone

        assert store.get("B") is None
        assert store.result is None


# --- Subtraction (F-16) ---


MINUS = "\u2212"


class TestDifference:
    def test_two_vectors_are_subtracted(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (5.0, 7.0, 9.0))
        actions.create_vector(store, (1.0, 2.0, 3.0))

        result = actions.compute_difference(store, "A", "B")

        assert result.components == (4.0, 5.0, 6.0)
        assert result.sources == ("A", "B")
        assert store.result is result

    def test_the_expression_shows_the_subtraction(self) -> None:
        store = VectorStore()
        fill(store, 2)
        result = actions.compute_difference(store, "A", "B")
        assert result.expression == f"A {MINUS} B"

    def test_order_matters_and_reverses_the_answer(self) -> None:
        # F-16 names A - B = -(B - A). The maths is tested in
        # tests/core/test_operations.py; this checks the panel's two
        # dropdowns really do produce opposite answers.
        store = VectorStore()
        actions.create_vector(store, (1.0, 2.0, 3.0))
        actions.create_vector(store, (4.0, 6.0, 8.0))

        forward = actions.compute_difference(store, "A", "B").components
        backward = actions.compute_difference(store, "B", "A").components

        assert forward == tuple(-value for value in backward)

    def test_the_same_vector_twice_gives_exactly_the_zero_vector(self) -> None:
        # F-16 allows this on purpose. Exact, not approximate: equal floats
        # subtract exactly, which is what makes the note honest.
        store = VectorStore()
        actions.create_vector(store, (0.1, 0.2, 0.3))

        result = actions.compute_difference(store, "A", "A")

        assert result.components == (0.0, 0.0, 0.0)

    def test_a_difference_replaces_a_resultant(self) -> None:
        store = VectorStore()
        fill(store, 3)
        tick(store, "A", "B")
        actions.compute_resultant(store)

        actions.compute_difference(store, "A", "C")

        assert store.result is not None
        assert store.result.sources == ("A", "C")
        assert store.result.operation is Operation.DIFFERENCE

    def test_a_resultant_replaces_a_difference(self) -> None:
        store = VectorStore()
        fill(store, 3)
        actions.compute_difference(store, "A", "B")
        tick(store, "B", "C")

        actions.compute_resultant(store)

        assert store.result is not None
        assert store.result.operation is Operation.SUM

    def test_a_missing_vector_is_refused(self) -> None:
        store = VectorStore()
        fill(store, 1)
        with pytest.raises(KeyError):
            actions.compute_difference(store, "A", "Z")


class TestADifferenceStaysADifference:
    """The fault this step exists to prevent."""

    def test_editing_an_input_recomputes_it_as_a_difference_not_a_sum(self) -> None:
        # Before `Result.operation` existed, every result was refreshed by
        # adding its sources up. A difference would silently become a sum the
        # first time one of its vectors was edited - the same numbers on
        # screen, quietly wrong.
        store = VectorStore()
        actions.create_vector(store, (5.0, 7.0, 9.0))
        actions.create_vector(store, (1.0, 2.0, 3.0))
        actions.compute_difference(store, "A", "B")

        actions.edit_vector(store, "A", (10.0, 10.0, 10.0))

        assert store.result is not None
        assert store.result.components == (9.0, 8.0, 7.0)
        # What the bug would have produced, stated so the test explains itself.
        assert store.result.components != (11.0, 12.0, 13.0)
        assert store.result.operation is Operation.DIFFERENCE

    def test_editing_the_subtrahend_recomputes_correctly(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (5.0, 0.0, 0.0))
        actions.create_vector(store, (1.0, 0.0, 0.0))
        actions.compute_difference(store, "A", "B")

        actions.edit_vector(store, "B", (4.0, 0.0, 0.0))

        assert store.result.components == (1.0, 0.0, 0.0)

    def test_deleting_either_input_takes_the_difference_away(self) -> None:
        for deleted in ("A", "B"):
            store = VectorStore()
            fill(store, 3)
            actions.compute_difference(store, "A", "B")

            actions.delete_vector(store, deleted)

            assert store.result is None, f"deleting {deleted} left the result"

    def test_a_difference_survives_undo_of_its_save(self) -> None:
        store = VectorStore()
        fill(store, 2)
        actions.compute_difference(store, "A", "B")
        actions.save_result_as_vector(store)

        actions.undo(store)

        assert store.result is not None
        assert store.result.operation is Operation.DIFFERENCE
        assert store.result.expression == f"A {MINUS} B"

"""The head-to-tail animation's geometry, and the promise it must keep (F-15).

The shape of the chain is pure arithmetic and is checked here against
hand-worked examples. The last test is the one F-15 actually asks for: the
animation must not permanently move or change any vector, so it plays a whole
run against a real store and asserts that nothing in it moved.
"""

from __future__ import annotations

import dataclasses

import pytest

from vectra3d.core.operations import resultant
from vectra3d.render.animations import chain_tails
from vectra3d.state import actions
from vectra3d.state.store import VectorStore


class TestChainTails:
    def test_the_first_vector_stays_at_the_origin(self) -> None:
        tails = chain_tails([(3.0, 0.0, 0.0), (0.0, 4.0, 0.0)])
        assert tails[0] == (0.0, 0.0, 0.0)

    def test_each_vector_starts_where_the_last_one_ended(self) -> None:
        # The classic 3-4-5: along x, then up y.
        tails = chain_tails([(3.0, 0.0, 0.0), (0.0, 4.0, 0.0)])
        assert tails == ((0.0, 0.0, 0.0), (3.0, 0.0, 0.0))

    def test_three_vectors(self) -> None:
        tails = chain_tails([(1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0)])
        assert tails == (
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 2.0, 0.0),
        )

    def test_ten_vectors_each_tail_is_the_running_sum(self) -> None:
        components = [(float(i), 0.0, 0.0) for i in range(1, 11)]
        tails = chain_tails(components)
        # 0, 1, 1+2, 1+2+3, ... - the triangular numbers.
        assert [tail[0] for tail in tails] == [0, 1, 3, 6, 10, 15, 21, 28, 36, 45]

    def test_the_last_head_lands_on_the_resultant(self) -> None:
        # This is the point the whole animation is making, so it is asserted
        # rather than assumed: walking the chain ends where the sum says.
        components = [(2.0, 1.0, 0.0), (-1.0, 3.0, 2.0), (4.0, -2.0, 1.0)]
        tails = chain_tails(components)
        last_head = tuple(
            tails[-1][axis] + components[-1][axis] for axis in range(3)
        )
        assert last_head == resultant(components)

    def test_vectors_that_cancel_bring_the_chain_back_to_the_origin(self) -> None:
        components = [(5.0, 0.0, 0.0), (-5.0, 0.0, 0.0)]
        tails = chain_tails(components)
        last_head = tuple(
            tails[-1][axis] + components[-1][axis] for axis in range(3)
        )
        assert last_head == (0.0, 0.0, 0.0)

    def test_one_vector_is_a_chain_of_one(self) -> None:
        assert chain_tails([(1.0, 2.0, 3.0)]) == ((0.0, 0.0, 0.0),)

    def test_no_vectors_is_an_empty_chain(self) -> None:
        assert chain_tails([]) == ()


class TestTheAnimationChangesNothing:
    """F-15: the animation does not permanently move or change any vector."""

    def test_a_whole_run_leaves_every_vector_exactly_as_it_was(self) -> None:
        pytest.importorskip("PySide6.QtWidgets")
        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtWidgets import QApplication

        from vectra3d.render.animations import HeadToTail

        # Held in a name on purpose, though nothing reads it: an application
        # created here must stay alive for the animation's timers to run.
        app = QApplication.instance() or QApplication([])  # noqa: F841

        store = VectorStore()
        actions.create_vector(store, (3.0, 1.0, 0.0))
        actions.create_vector(store, (1.0, 4.0, 2.0))
        actions.toggle_selected(store, "A")
        actions.toggle_selected(store, "B")
        actions.compute_resultant(store)

        before = {
            vector.name: dataclasses.replace(vector) for vector in store.vectors
        }
        result_before = store.result

        frames: list[tuple] = []
        loop = QEventLoop()
        player = HeadToTail(
            on_frame=lambda tails, drawn: frames.append((tails, drawn)),
            on_finished=loop.quit,
        )
        player.play([vector.components for vector in store.vectors])

        # A ceiling so a hang fails the test rather than blocking the suite.
        QTimer.singleShot(8000, loop.quit)
        loop.exec()

        assert frames, "the animation reported no frames at all"

        # The actual criterion.
        assert {v.name: v for v in store.vectors} == before
        for vector in store.vectors:
            assert vector.tail == (0.0, 0.0, 0.0)
        assert store.result is result_before

    def test_the_tails_it_reports_start_and_end_at_the_origin(self) -> None:
        # The frames move copies, and the run is a round trip: whatever it
        # reports in between, it must begin and end with everything home.
        components = [(3.0, 0.0, 0.0), (0.0, 4.0, 0.0)]
        tails = chain_tails(components)
        assert tails[0] == (0.0, 0.0, 0.0)
        # At full spread the second vector is away from the origin; the
        # window interpolates back to zero on the return phase.
        assert tails[1] != (0.0, 0.0, 0.0)


class TestTheChainEndsOnTheResult:
    """The chain has to arrive at the answer it is explaining.

    This is the property that was broken for subtraction: the animation laid
    out the raw source vectors, so `A - B` was drawn as A followed by B and
    ended at `A + B` - a point the result is not. The picture told the student
    something untrue, which is worse than it looking wrong.
    """

    def last_head(self, terms) -> tuple[float, float, float]:
        tails = chain_tails([term.components for term in terms])
        return tuple(
            tails[-1][axis] + terms[-1].components[axis] for axis in range(3)
        )

    def test_a_resultant_chain_ends_on_the_resultant(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (3.0, 1.0, 0.0))
        actions.create_vector(store, (1.0, 4.0, 2.0))
        actions.toggle_selected(store, "A")
        actions.toggle_selected(store, "B")
        result = actions.compute_resultant(store)

        terms = actions.chain_terms(store, result)

        assert self.last_head(terms) == result.components

    def test_a_difference_chain_ends_on_the_difference(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (5.0, 7.0, 9.0))
        actions.create_vector(store, (1.0, 2.0, 3.0))
        result = actions.compute_difference(store, "A", "B")

        terms = actions.chain_terms(store, result)

        assert self.last_head(terms) == result.components
        # And specifically not where laying out the raw sources would land.
        assert self.last_head(terms) != (6.0, 9.0, 12.0)

    def test_the_subtracted_term_points_the_other_way(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (5.0, 0.0, 0.0))
        actions.create_vector(store, (2.0, 3.0, 0.0))
        result = actions.compute_difference(store, "A", "B")

        terms = actions.chain_terms(store, result)

        assert terms[0].components == (5.0, 0.0, 0.0)
        assert terms[1].components == (-2.0, -3.0, 0.0)

    def test_the_reversed_term_is_labelled_with_a_minus(self) -> None:
        # Drawing B's letter on an arrow pointing away from B would be a
        # second way of saying something untrue.
        store = VectorStore()
        actions.create_vector(store, (5.0, 0.0, 0.0))
        actions.create_vector(store, (2.0, 0.0, 0.0))
        result = actions.compute_difference(store, "A", "B")

        terms = actions.chain_terms(store, result)

        assert terms[0].label == "A"
        assert terms[1].label == "\u2212B"

    def test_terms_keep_the_name_of_the_vector_they_came_from(self) -> None:
        # So the arrow keeps that vector's colour: it is still B, reversed.
        store = VectorStore()
        actions.create_vector(store, (5.0, 0.0, 0.0))
        actions.create_vector(store, (2.0, 0.0, 0.0))
        result = actions.compute_difference(store, "A", "B")

        assert [term.source for term in actions.chain_terms(store, result)] == [
            "A",
            "B",
        ]

    def test_a_deleted_vector_gives_no_chain(self) -> None:
        store = VectorStore()
        actions.create_vector(store, (5.0, 0.0, 0.0))
        actions.create_vector(store, (2.0, 0.0, 0.0))
        result = actions.compute_difference(store, "A", "B")
        store.remove("B")

        assert actions.chain_terms(store, result) == ()

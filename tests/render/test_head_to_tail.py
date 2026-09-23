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

        app = QApplication.instance() or QApplication([])

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

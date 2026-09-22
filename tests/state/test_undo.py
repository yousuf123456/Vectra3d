"""The history itself: stepping back and forward (F-19).

`History` knows nothing about vectors - it holds snapshots and hands them
back - so these tests use plain snapshots rather than a store. What each
action records is tested in `test_actions.py`.
"""

from __future__ import annotations

from vectra3d.state.models import Vector
from vectra3d.state.undo import MAX_STEPS, History, Snapshot


def snap(*names: str, active: str | None = None) -> Snapshot:
    """A snapshot holding one vector per name given."""
    vectors = {
        name: Vector(name=name, components=(float(index + 1), 0.0, 0.0))
        for index, name in enumerate(names)
    }
    return Snapshot(vectors=vectors, active=active)


# --- Nothing to do ---


def test_a_new_history_can_do_neither() -> None:
    history = History()
    assert history.can_undo is False
    assert history.can_redo is False


def test_undoing_nothing_returns_nothing() -> None:
    assert History().undo(snap("A")) is None


def test_redoing_nothing_returns_nothing() -> None:
    assert History().redo(snap("A")) is None


# --- Stepping back and forward ---


def test_a_recorded_step_can_be_undone() -> None:
    history = History()
    history.record(snap("A"))

    assert history.can_undo is True
    assert history.undo(snap("A", "B")).vectors.keys() == {"A"}


def test_undoing_makes_redo_available() -> None:
    history = History()
    history.record(snap("A"))
    history.undo(snap("A", "B"))

    assert history.can_redo is True


def test_redo_puts_back_what_undo_took_away() -> None:
    history = History()
    history.record(snap("A"))
    history.undo(snap("A", "B"))

    assert history.redo(snap("A")).vectors.keys() == {"A", "B"}


def test_a_round_trip_ends_where_it_started() -> None:
    history = History()
    before, after = snap("A"), snap("A", "B")
    history.record(before)

    undone = history.undo(after)
    assert undone.vectors.keys() == before.vectors.keys()
    assert history.redo(undone).vectors.keys() == after.vectors.keys()


def test_several_steps_come_back_in_reverse_order() -> None:
    history = History()
    history.record(snap("A"))
    history.record(snap("A", "B"))
    history.record(snap("A", "B", "C"))

    assert history.undo(snap("A", "B", "C", "D")).vectors.keys() == {"A", "B", "C"}
    assert history.undo(snap("A", "B", "C")).vectors.keys() == {"A", "B"}
    assert history.undo(snap("A", "B")).vectors.keys() == {"A"}
    assert history.can_undo is False


def test_the_active_vector_travels_with_the_snapshot() -> None:
    # Creating a vector makes it active, so undoing a create has to put the
    # highlight back where it was.
    history = History()
    history.record(snap("A", active="A"))

    assert history.undo(snap("A", "B", active="B")).active == "A"


# --- A new change abandons the redone branch ---


def test_recording_after_undoing_clears_redo() -> None:
    history = History()
    history.record(snap("A"))
    history.undo(snap("A", "B"))
    assert history.can_redo is True

    history.record(snap("A"))

    assert history.can_redo is False


def test_the_abandoned_branch_does_not_come_back() -> None:
    history = History()
    history.record(snap("A"))
    history.undo(snap("A", "B"))  # B is gone
    history.record(snap("A"))  # a new change instead

    assert history.redo(snap("A", "C")) is None


# --- The twenty-step limit ---


def test_the_history_stops_at_the_limit() -> None:
    history = History()
    for step in range(MAX_STEPS + 5):
        history.record(snap("A", active=str(step)))

    for _ in range(MAX_STEPS):
        assert history.can_undo is True
        history.undo(snap("A"))

    assert history.can_undo is False


def test_the_oldest_steps_are_the_ones_lost() -> None:
    # Twenty-five changes, so the first five fall off and the oldest step
    # still reachable is the sixth.
    history = History()
    for step in range(MAX_STEPS + 5):
        history.record(snap("A", active=str(step)))

    last = None
    while history.can_undo:
        last = history.undo(snap("A"))

    assert last.active == "5"


def test_the_limit_is_twenty() -> None:
    # F-19 names the number, so it is asserted rather than assumed.
    assert MAX_STEPS == 20

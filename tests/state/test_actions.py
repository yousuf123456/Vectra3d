"""The allowed changes to vectors (`architecture.md` section 2)."""

from __future__ import annotations

import dataclasses

import pytest

from vectra3d.state import actions, naming
from vectra3d.state.models import ORIGIN, Vector
from vectra3d.state.store import VectorStore


def fill(store: VectorStore, count: int) -> None:
    for i in range(count):
        actions.create_vector(store, (float(i + 1), 0.0, 0.0))


# --- Creating ---


def test_the_first_vector_is_a() -> None:
    store = VectorStore()
    vector = actions.create_vector(store, (1.0, 2.0, 3.0))
    assert vector.name == "A"
    assert vector.components == (1.0, 2.0, 3.0)
    assert store.count == 1


def test_a_new_vector_starts_at_the_origin() -> None:
    # Always the origin in the MVP, but stored rather than assumed so that
    # free vectors can be added later (`project-overview.md`).
    store = VectorStore()
    vector = actions.create_vector(store, (1.0, 2.0, 3.0))
    assert vector.tail == ORIGIN


def test_a_new_vector_becomes_active() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.create_vector(store, (0.0, 1.0, 0.0))
    assert store.active_name == "B"


def test_a_deleted_letter_is_reused() -> None:
    store = VectorStore()
    fill(store, 3)  # A, B, C
    actions.delete_vector(store, "B")
    assert actions.create_vector(store, (7.0, 0.0, 0.0)).name == "B"


def test_the_eleventh_vector_is_refused() -> None:
    store = VectorStore()
    fill(store, naming.MAX_VECTORS)
    assert store.count == 10

    assert actions.create_vector(store, (1.0, 1.0, 1.0)) is None
    assert store.count == 10


def test_a_zero_vector_can_be_created() -> None:
    # Typed input rejects it (F-04), but a result can be zero and be saved
    # as a vector (F-16), so the store itself must allow it.
    store = VectorStore()
    assert actions.create_vector(store, (0.0, 0.0, 0.0)) is not None


def test_a_vector_cannot_be_changed_in_place() -> None:
    store = VectorStore()
    vector = actions.create_vector(store, (1.0, 0.0, 0.0))
    with pytest.raises(dataclasses.FrozenInstanceError):
        vector.components = (9.0, 0.0, 0.0)


# --- Deleting ---


def test_deleting_removes_only_that_vector() -> None:
    store = VectorStore()
    fill(store, 3)
    assert actions.delete_vector(store, "B") is True
    assert store.names == ("A", "C")


def test_deleting_a_vector_that_does_not_exist_changes_nothing() -> None:
    store = VectorStore()
    fill(store, 1)
    assert actions.delete_vector(store, "D") is False
    assert store.names == ("A",)


def test_deleting_the_active_vector_activates_the_first_one_left() -> None:
    store = VectorStore()
    fill(store, 3)  # C is active
    actions.delete_vector(store, "C")
    assert store.active_name == "A"


def test_deleting_an_inactive_vector_leaves_the_active_one_alone() -> None:
    store = VectorStore()
    fill(store, 3)
    actions.delete_vector(store, "A")
    assert store.active_name == "C"


def test_deleting_the_last_vector_leaves_nothing_active() -> None:
    store = VectorStore()
    fill(store, 1)
    actions.delete_vector(store, "A")
    assert store.active is None


# --- Clearing ---


def test_clear_all_empties_the_scene() -> None:
    store = VectorStore()
    fill(store, 4)
    actions.clear_all(store)
    assert store.vectors == ()
    assert store.active is None


def test_names_start_again_after_clearing() -> None:
    store = VectorStore()
    fill(store, 4)
    actions.clear_all(store)
    assert actions.create_vector(store, (1.0, 0.0, 0.0)).name == "A"


# --- The active vector ---


def test_the_active_vector_can_be_changed() -> None:
    store = VectorStore()
    fill(store, 3)
    actions.set_active(store, "A")
    assert store.active_name == "A"


def test_an_absent_vector_cannot_be_made_active() -> None:
    store = VectorStore()
    fill(store, 1)
    with pytest.raises(KeyError):
        actions.set_active(store, "B")


# --- Editing ---


def test_editing_replaces_the_components() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 2.0, 3.0))

    assert actions.edit_vector(store, "A", (-4.0, 0.5, 7.0)) is True
    assert store.get("A").components == (-4.0, 0.5, 7.0)


def test_an_edited_vector_keeps_its_name_tail_and_lock() -> None:
    store = VectorStore()
    store.put(Vector(name="B", components=(1.0, 0.0, 0.0), tail=ORIGIN))
    before = store.get("B")

    actions.edit_vector(store, "B", (0.0, 5.0, 0.0))

    after = store.get("B")
    assert (after.name, after.tail, after.locked) == (
        before.name,
        before.tail,
        before.locked,
    )


def test_editing_does_not_add_or_remove_vectors() -> None:
    store = VectorStore()
    fill(store, 3)

    actions.edit_vector(store, "B", (0.0, 0.0, 9.0))

    assert store.names == ("A", "B", "C")


def test_a_locked_vector_refuses_to_be_edited() -> None:
    store = VectorStore()
    store.put(Vector(name="A", components=(1.0, 0.0, 0.0), locked=True))

    assert actions.edit_vector(store, "A", (9.0, 9.0, 9.0)) is False
    assert store.get("A").components == (1.0, 0.0, 0.0)


def test_an_absent_vector_cannot_be_edited() -> None:
    store = VectorStore()

    assert actions.edit_vector(store, "A", (1.0, 1.0, 1.0)) is False


def test_editing_leaves_the_active_vector_and_the_ticks_alone() -> None:
    store = VectorStore()
    fill(store, 3)
    actions.set_active(store, "C")
    actions.toggle_selected(store, "A")

    actions.edit_vector(store, "A", (0.0, 0.0, 1.0))

    assert store.active_name == "C"
    assert store.selected == ("A",)


def test_a_refused_edit_notifies_nothing() -> None:
    store = VectorStore()
    store.put(Vector(name="A", components=(1.0, 0.0, 0.0), locked=True))
    calls: list[None] = []
    store.subscribe(lambda: calls.append(None))

    actions.edit_vector(store, "A", (2.0, 0.0, 0.0))

    assert calls == []


def test_a_vector_can_be_edited_to_zero() -> None:
    # The store takes it; the typed form is what refuses a zero vector (F-04),
    # because an operation result in G3 can legitimately be zero.
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))

    assert actions.edit_vector(store, "A", (0.0, 0.0, 0.0)) is True


# --- Locking (F-09a) ---


def test_a_vector_starts_unlocked() -> None:
    store = VectorStore()
    vector = actions.create_vector(store, (1.0, 0.0, 0.0))
    assert vector.locked is False


def test_locking_and_unlocking_report_the_new_state() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))

    assert actions.toggle_locked(store, "A") is True
    assert store.get("A").locked is True
    assert actions.toggle_locked(store, "A") is False
    assert store.get("A").locked is False


def test_locking_keeps_everything_else_about_the_vector() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 2.0, 3.0))
    before = store.get("A")

    actions.toggle_locked(store, "A")

    after = store.get("A")
    assert (after.name, after.components, after.tail) == (
        before.name,
        before.components,
        before.tail,
    )


def test_an_absent_vector_cannot_be_locked() -> None:
    store = VectorStore()
    with pytest.raises(KeyError):
        actions.toggle_locked(store, "A")


def test_locking_leaves_the_active_vector_and_the_ticks_alone() -> None:
    store = VectorStore()
    fill(store, 3)
    actions.set_active(store, "C")
    actions.toggle_selected(store, "A")

    actions.toggle_locked(store, "A")

    assert store.active_name == "C"
    assert store.selected == ("A",)


def test_a_locked_vector_can_still_be_made_active() -> None:
    # F-09a: locking stops it changing, not it being chosen.
    store = VectorStore()
    fill(store, 2)
    actions.toggle_locked(store, "B")

    actions.set_active(store, "B")

    assert store.active_name == "B"


def test_a_locked_vector_can_still_be_ticked() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.toggle_locked(store, "A")

    assert actions.toggle_selected(store, "A") is True


# --- Locking protects against deletion (F-09a) ---


def test_a_locked_vector_refuses_to_be_deleted() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.toggle_locked(store, "A")

    assert actions.delete_vector(store, "A") is False
    assert store.names == ("A",)


def test_unlocking_lets_it_be_deleted_again() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.toggle_locked(store, "A")
    actions.toggle_locked(store, "A")

    assert actions.delete_vector(store, "A") is True
    assert store.names == ()


def test_a_refused_deletion_notifies_nothing() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 0.0, 0.0))
    actions.toggle_locked(store, "A")
    calls: list[None] = []
    store.subscribe(lambda: calls.append(None))

    actions.delete_vector(store, "A")

    assert calls == []


def test_a_refused_deletion_does_not_move_the_active_vector() -> None:
    store = VectorStore()
    fill(store, 2)
    actions.set_active(store, "A")
    actions.toggle_locked(store, "A")

    actions.delete_vector(store, "A")

    assert store.active_name == "A"


def test_clear_all_still_removes_locked_vectors() -> None:
    # F-10 promises this, and the Clear all prompt says so.
    store = VectorStore()
    fill(store, 3)
    actions.toggle_locked(store, "B")

    actions.clear_all(store)

    assert store.names == ()


# --- Change events ---


@pytest.mark.parametrize(
    "act",
    [
        lambda s: actions.create_vector(s, (1.0, 0.0, 0.0)),
        lambda s: actions.delete_vector(s, "A"),
        lambda s: actions.clear_all(s),
        lambda s: actions.set_active(s, "A"),
        lambda s: actions.edit_vector(s, "A", (9.0, 9.0, 9.0)),
        lambda s: actions.toggle_locked(s, "A"),
    ],
)
def test_every_action_notifies_once(act) -> None:
    store = VectorStore()
    store.put(Vector(name="A", components=(1.0, 0.0, 0.0)))
    store.set_active("A")

    calls: list[None] = []
    store.subscribe(lambda: calls.append(None))

    act(store)

    assert len(calls) == 1


def test_a_refused_creation_changes_nothing_and_notifies_nothing() -> None:
    store = VectorStore()
    fill(store, naming.MAX_VECTORS)
    calls: list[None] = []
    store.subscribe(lambda: calls.append(None))

    actions.create_vector(store, (1.0, 1.0, 1.0))

    assert calls == []
    assert store.active_name == "J"

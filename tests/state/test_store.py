"""Storage and change notification (`architecture.md` section 2)."""

from __future__ import annotations

import pytest

from vectra3d.state.models import Vector
from vectra3d.state.store import VectorStore


def make_store(*names: str) -> VectorStore:
    store = VectorStore()
    for i, name in enumerate(names, start=1):
        store.put(Vector(name=name, components=(float(i), 0.0, 0.0)))
    return store


def test_a_new_store_is_empty() -> None:
    store = VectorStore()
    assert store.vectors == ()
    assert store.count == 0
    assert store.active is None
    assert store.active_name is None


def test_vectors_are_listed_in_name_order() -> None:
    # C was added before B, but B is shown first.
    store = make_store("A", "C", "B")
    assert store.names == ("A", "B", "C")
    assert [v.name for v in store.vectors] == ["A", "B", "C"]


def test_put_replaces_the_vector_with_the_same_name() -> None:
    store = make_store("A")
    store.put(Vector(name="A", components=(9.0, 9.0, 9.0)))
    assert store.count == 1
    assert store.get("A").components == (9.0, 9.0, 9.0)


def test_get_returns_none_for_a_missing_vector() -> None:
    assert VectorStore().get("A") is None


def test_active_follows_the_named_vector() -> None:
    store = make_store("A", "B")
    store.set_active("B")
    assert store.active_name == "B"
    assert store.active.components == (2.0, 0.0, 0.0)


def test_a_vector_that_does_not_exist_cannot_be_made_active() -> None:
    with pytest.raises(KeyError):
        VectorStore().set_active("A")


def test_listeners_are_called_on_notify() -> None:
    store = VectorStore()
    calls: list[int] = []
    store.subscribe(lambda: calls.append(1))
    store.subscribe(lambda: calls.append(2))

    store.notify()

    assert calls == [1, 2]


def test_changing_the_store_does_not_notify_on_its_own() -> None:
    # Notifying is the action's job, once, after all of its changes are made.
    store = VectorStore()
    calls: list[None] = []
    store.subscribe(lambda: calls.append(None))

    store.put(Vector(name="A", components=(1.0, 0.0, 0.0)))
    store.set_active("A")

    assert calls == []

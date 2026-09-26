"""Gesture settings in the store (F-20, `interaction-spec.md` section 8)."""

from __future__ import annotations

import pytest

from vectra3d import config
from vectra3d.state import actions
from vectra3d.state.models import Settings
from vectra3d.state.store import VectorStore


def test_a_new_store_starts_at_the_specs_defaults() -> None:
    settings = VectorStore().settings
    assert settings == Settings(snapping=True, sensitivity=25)
    assert settings.snapping is config.SNAPPING_DEFAULT
    assert settings.sensitivity == config.MAGNITUDE_SENSITIVITY_DEFAULT


def test_snapping_can_be_turned_off_and_on() -> None:
    store = VectorStore()
    actions.set_snapping(store, False)
    assert not store.settings.snapping
    actions.set_snapping(store, True)
    assert store.settings.snapping


@pytest.mark.parametrize("units", [5, 10, 25, 45, 50])
def test_every_step_from_5_to_50_is_accepted(units: int) -> None:
    store = VectorStore()
    assert actions.set_sensitivity(store, units)
    assert store.settings.sensitivity == units


@pytest.mark.parametrize("units", [0, 4, 7, 55, -5])
def test_values_off_the_grid_are_refused_and_change_nothing(units: int) -> None:
    store = VectorStore()
    assert not actions.set_sensitivity(store, units)
    assert store.settings.sensitivity == 25


def test_changing_a_setting_is_not_an_undo_step_and_tells_nobody() -> None:
    store = VectorStore()
    heard = []
    store.subscribe(lambda: heard.append(True))
    actions.set_snapping(store, False)
    actions.set_sensitivity(store, 40)
    assert not store.history.can_undo
    assert heard == []


def test_settings_survive_clearing_and_undo() -> None:
    store = VectorStore()
    actions.create_vector(store, (1.0, 2.0, 3.0))
    actions.set_snapping(store, False)
    actions.set_sensitivity(store, 10)
    actions.clear_all(store)
    actions.undo(store)
    actions.undo(store)
    assert store.settings == Settings(snapping=False, sensitivity=10)

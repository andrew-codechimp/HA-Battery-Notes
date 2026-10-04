"""Tests for battery notes storage save scheduling."""

from __future__ import annotations

from unittest.mock import MagicMock

from custom_components.battery_notes.store import (
    REPORTED_SAVE_DELAY,
    SAVE_DELAY,
    BatteryNotesStorage,
)


def _storage() -> tuple[BatteryNotesStorage, MagicMock, list[float]]:
    """Create a storage with a mocked store and a controllable loop clock."""
    now = [1000.0]
    hass = MagicMock()
    hass.loop.time.side_effect = lambda: now[0]

    storage = BatteryNotesStorage.__new__(BatteryNotesStorage)
    storage.hass = hass
    storage.devices = {}
    storage.entities = {}
    storage._save_due = None  # noqa: SLF001
    store = MagicMock()
    storage._store = store  # noqa: SLF001

    return storage, store, now


def _delays(store: MagicMock) -> list[float]:
    return [call.args[1] for call in store.async_delay_save.call_args_list]


def test_reported_updates_are_batched() -> None:
    """Frequent reported updates schedule a single save instead of postponing it."""
    storage, store, now = _storage()

    storage.async_create_device("device", {}, REPORTED_SAVE_DELAY)
    for _ in range(5):
        now[0] += 60
        storage.async_update_device(
            "device", {"battery_last_reported_level": 50}, REPORTED_SAVE_DELAY
        )

    assert _delays(store) == [REPORTED_SAVE_DELAY]


def test_user_change_saves_sooner() -> None:
    """A change with the default delay brings a pending batched save forward."""
    storage, store, _ = _storage()

    storage.async_create_device("device", {}, REPORTED_SAVE_DELAY)
    storage.async_update_device("device", {"battery_last_replaced": None})

    assert _delays(store) == [REPORTED_SAVE_DELAY, SAVE_DELAY]


def test_reported_update_keeps_pending_user_save() -> None:
    """A reported update doesn't push back an earlier pending save."""
    storage, store, _ = _storage()

    storage.async_create_device("device", {})
    storage.async_update_device(
        "device", {"battery_last_reported_level": 50}, REPORTED_SAVE_DELAY
    )

    assert _delays(store) == [SAVE_DELAY]


def test_change_after_write_schedules_again() -> None:
    """Once the data is written, the next change schedules a new save."""
    storage, store, _ = _storage()

    storage.async_create_device("device", {}, REPORTED_SAVE_DELAY)
    data_func = store.async_delay_save.call_args.args[0]
    data = data_func()
    assert data["devices"][0]["device_id"] == "device"

    storage.async_update_device(
        "device", {"battery_last_reported_level": 50}, REPORTED_SAVE_DELAY
    )

    assert _delays(store) == [REPORTED_SAVE_DELAY, REPORTED_SAVE_DELAY]

"""Tests for loading and saving Battery Notes storage."""

from datetime import datetime, timedelta
from typing import Any, NamedTuple

import pytest
from custom_components.battery_notes.const import (
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    LAST_REPLACED,
    LAST_REPORTED_LEVEL,
    SERVICE_BATTERY_REPLACED,
)
from custom_components.battery_notes.store import (
    REPORTED_SAVE_DELAY,
    SAVE_DELAY,
    STORAGE_KEY,
    STORAGE_VERSION_MAJOR,
    STORAGE_VERSION_MINOR,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep the default replacement time distinct from the stored one."""
    freezer.move_to("2026-01-01T12:00:00+00:00")


@pytest.mark.parametrize(
    "stored",
    [
        pytest.param(
            (
                STORAGE_VERSION_MINOR,
                {
                    LAST_REPLACED: "2025-06-01T10:00:00+00:00",
                    "battery_last_reported": None,
                    "battery_last_reported_level": None,
                    "field_from_a_newer_version": True,
                },
            ),
            id="unknown-field",
        ),
        pytest.param(
            (1, {LAST_REPLACED: "2025-06-01T10:00:00:000000+00:00"}),
            id="old-missing-fields",
        ),
    ],
)
@pytest.mark.parametrize("battery_note_source", ["device"])
async def test_load_storage(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    stored: tuple[int, dict[str, Any]],
) -> None:
    """Test storage with unknown or missing fields loads its battery notes."""
    minor_version, stored_device = stored
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION_MAJOR,
        "minor_version": minor_version,
        "key": STORAGE_KEY,
        "data": {
            "devices": [{"device_id": battery_note_device.id, **stored_device}],
            "entities": [],
        },
    }

    await setup_integration(hass, battery_note_config_entry)

    assert battery_note_config_entry.state is ConfigEntryState.LOADED
    coordinator = next(
        iter(battery_note_config_entry.runtime_data.subentry_coordinators.values())
    )
    assert coordinator.last_replaced == datetime.fromisoformat(
        "2025-06-01T10:00:00+00:00"
    )


async def _advance_time(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: int
) -> None:
    """Run scheduled storage writes after advancing Home Assistant's clock."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done(wait_background_tasks=True)


class StorageNote(NamedTuple):
    """Source and persisted collection of a loaded battery note."""

    entity_id: str
    collection: str
    replacement_target: dict[str, str]


@pytest.fixture
async def storage_note(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_note_source: str,
    freezer: FrozenDateTimeFactory,
) -> StorageNote:
    """Load a note and let its initial battery history persist."""
    await setup_integration(hass, battery_note_config_entry)
    await _advance_time(hass, freezer, SAVE_DELAY)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    target_field, collection = {
        "device": (CONF_DEVICE_ID, "devices"),
        "entity": (CONF_SOURCE_ENTITY_ID, "entities"),
        "standalone-entity": (CONF_SOURCE_ENTITY_ID, "entities"),
    }[battery_note_source]
    return StorageNote(
        battery_note_sensor.entity_id,
        collection,
        {target_field: subentry.data[target_field]},
    )


async def _report_level(hass: HomeAssistant, note: StorageNote, level: float) -> None:
    """Publish a source battery report through Home Assistant."""
    state = hass.states.get(note.entity_id)
    assert state is not None
    hass.states.async_set(note.entity_id, str(level), state.attributes)
    await hass.async_block_till_done()


async def _replace_battery(hass: HomeAssistant, note: StorageNote) -> None:
    """Record a replacement through the integration's Home Assistant action."""
    await hass.services.async_call(
        DOMAIN, SERVICE_BATTERY_REPLACED, note.replacement_target, blocking=True
    )
    await hass.async_block_till_done()


def _saved_note(hass_storage: dict[str, Any], note: StorageNote) -> dict[str, Any]:
    """Read the battery history actually written to Home Assistant storage."""
    return hass_storage[STORAGE_KEY]["data"][note.collection][0]


async def test_reported_updates_are_batched(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
    storage_note: StorageNote,
) -> None:
    """Test frequent reports persist by the first deadline and can save again."""
    assert _saved_note(hass_storage, storage_note)[LAST_REPORTED_LEVEL] == 55.0
    await _report_level(hass, storage_note, 50.0)

    for level in (49.0, 48.0, 47.0, 46.0, 45.0):
        await _advance_time(hass, freezer, 60)
        await _report_level(hass, storage_note, level)
        assert _saved_note(hass_storage, storage_note)[LAST_REPORTED_LEVEL] == 55.0

    await _advance_time(hass, freezer, REPORTED_SAVE_DELAY - 5 * 60 - 1)
    assert _saved_note(hass_storage, storage_note)[LAST_REPORTED_LEVEL] == 55.0
    await _advance_time(hass, freezer, 1)
    assert _saved_note(hass_storage, storage_note)[LAST_REPORTED_LEVEL] == 45.0

    await _report_level(hass, storage_note, 40.0)
    await _advance_time(hass, freezer, REPORTED_SAVE_DELAY - 1)
    assert _saved_note(hass_storage, storage_note)[LAST_REPORTED_LEVEL] == 45.0
    await _advance_time(hass, freezer, 1)
    assert _saved_note(hass_storage, storage_note)[LAST_REPORTED_LEVEL] == 40.0


@pytest.mark.parametrize(
    "schedule",
    [
        pytest.param(
            ("report", "replace", SAVE_DELAY, 1), id="user-change-saves-sooner"
        ),
        pytest.param(
            ("replace", "report", SAVE_DELAY - 1, 0),
            id="report-keeps-user-deadline",
        ),
    ],
)
async def test_earliest_save_deadline(
    hass: HomeAssistant,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
    storage_note: StorageNote,
    schedule: tuple[str, str, int, int],
) -> None:
    """Test reports and user changes persist together at the earlier deadline."""
    first_operation, second_operation, remaining_delay, replacement_offset = schedule
    original = _saved_note(hass_storage, storage_note).copy()
    replaced_at = dt_util.utcnow() + timedelta(seconds=replacement_offset)
    operations = {
        "report": lambda: _report_level(hass, storage_note, 50.0),
        "replace": lambda: _replace_battery(hass, storage_note),
    }
    await operations[first_operation]()
    await _advance_time(hass, freezer, 1)
    await operations[second_operation]()

    await _advance_time(hass, freezer, remaining_delay - 1)
    assert _saved_note(hass_storage, storage_note) == original
    await _advance_time(hass, freezer, 1)
    saved = _saved_note(hass_storage, storage_note)
    assert saved[LAST_REPORTED_LEVEL] == 50.0
    assert datetime.fromisoformat(saved[LAST_REPLACED]) == replaced_at

"""Tests for loading Battery Notes storage."""

from datetime import datetime
from typing import Any

import pytest
from custom_components.battery_notes.const import LAST_REPLACED
from custom_components.battery_notes.store import (
    STORAGE_KEY,
    STORAGE_VERSION_MAJOR,
    STORAGE_VERSION_MINOR,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

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

"""Tests for Battery Notes diagnostics."""

import pytest
from custom_components.battery_notes.library import DATA_LIBRARY
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

SOURCE_ENTITY_ID = "sensor.door_battery"
SNAPSHOT_EXCLUDE = props("entry_id", "device_id", "created_at", "modified_at")


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep the reported and replaced timestamps stable in snapshots."""
    freezer.move_to("2026-01-01T12:00:00+00:00")


@pytest.fixture
def battery_note_device(
    battery_note_device: dr.DeviceEntry, device_registry: dr.DeviceRegistry
) -> dr.DeviceEntry:
    """Include model ID and hardware version in the source device details."""
    return device_registry.async_update_device(
        battery_note_device.id, model_id="DS-01", hw_version="1.2.3"
    )


async def test_entry_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test downloading diagnostics for an entry without battery notes."""
    await setup_integration(hass, mock_config_entry)

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, mock_config_entry
    )
    assert diagnostics["entry"]["entry_id"] == mock_config_entry.entry_id
    assert diagnostics == snapshot(exclude=SNAPSHOT_EXCLUDE)


async def test_note_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    battery_note_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test downloading entry data and source device details for saved notes."""
    await setup_integration(hass, battery_note_config_entry)

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, battery_note_config_entry
    )
    assert diagnostics["entry"]["entry_id"] == battery_note_config_entry.entry_id
    assert diagnostics["entry"]["subentries"] == [
        subentry.as_dict() for subentry in battery_note_config_entry.subentries.values()
    ]
    assert diagnostics == snapshot(exclude=SNAPSHOT_EXCLUDE)


@pytest.mark.parametrize(
    "battery_note_source",
    [
        pytest.param("entity", id="entity-with-device"),
        pytest.param("standalone-entity", id="standalone-entity"),
    ],
)
async def test_missing_source_entity(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    battery_note_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test a missing entity falls back to the saved device when available."""
    er.async_get(hass).async_remove(SOURCE_ENTITY_ID)
    await hass.async_block_till_done()
    await setup_integration(hass, battery_note_config_entry)

    assert await get_diagnostics_for_config_entry(
        hass, hass_client, battery_note_config_entry
    ) == snapshot(exclude=SNAPSHOT_EXCLUDE)


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_missing_source_device(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    battery_note_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test a missing device does not prevent downloading the saved entry."""
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    dr.async_get(hass).async_remove_device(subentry.data[CONF_DEVICE_ID])
    await hass.async_block_till_done()
    await setup_integration(hass, battery_note_config_entry)

    assert await get_diagnostics_for_config_entry(
        hass, hass_client, battery_note_config_entry
    ) == snapshot(exclude=SNAPSHOT_EXCLUDE)


@pytest.mark.parametrize("battery_note_source", [pytest.param("entity", id="entity")])
async def test_entity_device_takes_precedence(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test an entity's current device takes precedence over the saved device ID."""
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=next(iter(battery_note_device.config_entries)),
        identifiers={("test", "replacement-device")},
        name="Replacement door sensor",
        manufacturer="Replacement Manufacturer",
        model="Replacement sensor",
        model_id="DS-02",
        hw_version="2.0",
    )
    er.async_get(hass).async_update_entity(SOURCE_ENTITY_ID, device_id=device.id)
    await hass.async_block_till_done()
    await setup_integration(hass, battery_note_config_entry)

    assert await get_diagnostics_for_config_entry(
        hass, hass_client, battery_note_config_entry
    ) == snapshot(exclude=SNAPSHOT_EXCLUDE)


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_library_match(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
) -> None:
    """Test the library entry matching the source device is included."""
    dr.async_get(hass).async_update_device(
        battery_note_device.id,
        model="Specific sensor",
        model_id="S1",
        hw_version="Rev2",
    )
    await setup_integration(hass, battery_note_config_entry)
    await hass.data[DATA_LIBRARY].load_libraries()
    subentry = next(iter(battery_note_config_entry.subentries.values()))

    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, battery_note_config_entry
    )

    assert diagnostics["library_loaded"] is True
    assert diagnostics["sub_entries"][subentry.subentry_id]["library_match"] == {
        "manufacturer": "Test Manufacturer",
        "model": "Specific sensor",
        "model_id": "S1",
        "hw_version": "Rev2",
        "battery_type": "CR2032",
        "battery_quantity": 4,
    }

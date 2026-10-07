"""Tests for the Battery Notes button platform."""

from dataclasses import replace
from unittest.mock import patch

import pytest
from custom_components.battery_notes.const import (
    ATTR_AREA_NAME,
    ATTR_BATTERY_LAST_REPLACED,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_NOTE,
    ATTR_SOURCE_ENTITY_ID,
    CONF_ADVANCED_SETTINGS,
    CONF_ENABLE_REPLACED,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_REPLACED,
    LAST_REPLACED,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.const import ATTR_ENTITY_ID, CONF_DEVICE_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

SOURCE_ENTITY_ID = "sensor.door_battery"
BUTTON_UNIQUE_ID = "bn_door_battery_battery_replaced_button"


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep the default replacement date stable."""
    freezer.move_to("2026-01-01T12:00:00+00:00")


async def test_entities(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    mock_battery_note_subentry: ConfigSubentry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the button state, metadata, and source association."""
    with patch("custom_components.battery_notes.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(hass, battery_note_config_entry)

    assert battery_note_config_entry.state is ConfigEntryState.LOADED
    entries = er.async_entries_for_config_entry(
        entity_registry, battery_note_config_entry.entry_id
    )
    assert len(entries) == 1
    assert entries[0].config_subentry_id == mock_battery_note_subentry.subentry_id
    assert entries[0].device_id == mock_battery_note_subentry.data.get(CONF_DEVICE_ID)

    await snapshot_platform(
        hass, entity_registry, snapshot, battery_note_config_entry.entry_id
    )


@pytest.mark.parametrize(
    "mock_config_entry",
    [{CONF_ADVANCED_SETTINGS: {CONF_ENABLE_REPLACED: False}}],
    indirect=True,
)
async def test_disabled_by_default(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test disabling replacement tracking leaves the button disabled in the registry."""
    with patch("custom_components.battery_notes.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(hass, battery_note_config_entry)

    entity_id = entity_registry.async_get_entity_id(
        BUTTON_DOMAIN, DOMAIN, BUTTON_UNIQUE_ID
    )
    assert entity_id is not None
    entry = entity_registry.async_get(entity_id)
    assert entry is not None
    assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None


async def test_orphaned_note(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    entity_registry: er.EntityRegistry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test a missing source prevents creation of the button."""
    entity_registry.async_remove(SOURCE_ENTITY_ID)
    device_registry.async_remove_device(battery_note_device.id)
    await hass.async_block_till_done()

    with patch("custom_components.battery_notes.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(hass, battery_note_config_entry)

    assert battery_note_config_entry.state is ConfigEntryState.LOADED
    assert not er.async_entries_for_config_entry(
        entity_registry, battery_note_config_entry.entry_id
    )


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_other_subentry_type(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test subentries of another type do not create buttons."""
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    other_subentry = replace(subentry, subentry_type="other")
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=battery_note_config_entry.version,
        options=battery_note_config_entry.options,
        subentries_data=[other_subentry.as_dict()],
    )
    with patch("custom_components.battery_notes.PLATFORMS", [Platform.BUTTON]):
        await setup_integration(hass, entry)

    assert entry.state is ConfigEntryState.LOADED
    assert not er.async_entries_for_config_entry(entity_registry, entry.entry_id)


@pytest.mark.parametrize(
    "battery_note_area",
    [pytest.param(None, id="no-area"), pytest.param("Hall", id="with-area")],
    indirect=True,
)
async def test_press_battery_replaced_button(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    battery_note_area: str | None,
) -> None:
    """Test the button press service updates storage, sensors, and the event."""
    await setup_integration(hass, battery_note_config_entry)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    button_id = entity_registry.async_get_entity_id(
        BUTTON_DOMAIN, DOMAIN, BUTTON_UNIQUE_ID
    )
    assert button_id is not None
    battery_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{subentry.unique_id}_battery_plus"
    )
    assert battery_id is not None
    battery_before = hass.states.get(battery_id)
    assert battery_before is not None
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)
    freezer.move_to("2026-01-02T14:30:00+00:00")
    pressed_at = dt_util.utcnow()

    await hass.services.async_call(
        BUTTON_DOMAIN, SERVICE_PRESS, {ATTR_ENTITY_ID: button_id}, blocking=True
    )
    await hass.async_block_till_done()

    button = hass.states.get(button_id)
    assert button is not None
    assert button.state == pressed_at.isoformat()
    coordinator = battery_note_config_entry.runtime_data.subentry_coordinators[
        subentry.subentry_id
    ]
    assert coordinator.last_replaced == pressed_at
    store = battery_note_config_entry.runtime_data.store
    stored_entries = {**store.async_get_devices(), **store.async_get_entities()}
    source_key = (
        subentry.data.get(CONF_SOURCE_ENTITY_ID) or subentry.data[CONF_DEVICE_ID]
    )
    assert stored_entries[source_key][LAST_REPLACED] == pressed_at
    battery_after = hass.states.get(battery_id)
    assert battery_after is not None
    assert battery_after.state == battery_before.state
    assert battery_after.attributes[ATTR_BATTERY_LAST_REPLACED] == pressed_at
    assert battery_before.attributes[ATTR_BATTERY_LAST_REPLACED] != pressed_at
    assert len(events) == 1
    assert events[0].data == {
        ATTR_DEVICE_ID: subentry.data.get(CONF_DEVICE_ID, ""),
        ATTR_SOURCE_ENTITY_ID: subentry.data.get(CONF_SOURCE_ENTITY_ID, ""),
        ATTR_AREA_NAME: battery_note_area,
        ATTR_DEVICE_NAME: "Door battery note",
        ATTR_BATTERY_TYPE_AND_QUANTITY: "2× AA",
        ATTR_BATTERY_TYPE: "AA",
        ATTR_BATTERY_QUANTITY: 2,
        ATTR_NOTE: "",
    }

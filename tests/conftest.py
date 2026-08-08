"""Battery Notes tests configuration."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.battery_notes.config_flow import CONFIG_VERSION
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_ENABLE_REPLACED,
    CONF_FILTER_OUTLIERS,
    CONF_HIDE_BATTERY,
    CONF_HIDE_BATTERY_LOW,
    CONF_ROUND_BATTERY,
    CONF_SHOW_ALL_DEVICES,
    CONF_USER_LIBRARY,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DOMAIN,
    SUBENTRY_BATTERY_NOTE,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER, ConfigEntry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):  # noqa: ARG001
    """Enable loading custom integrations."""
    yield  # noqa: PT022


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Mock async_setup_entry for Battery Notes config flow tests."""
    with patch(
        "custom_components.battery_notes.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
async def mock_config_entry(
    hass: HomeAssistant,
) -> MockConfigEntry:
    """Create a Battery Notes config entry without subentries."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        version=CONFIG_VERSION,
        options={
            CONF_SHOW_ALL_DEVICES: False,
            CONF_HIDE_BATTERY: False,
            CONF_ROUND_BATTERY: False,
            CONF_DEFAULT_BATTERY_LOW_THRESHOLD: DEFAULT_BATTERY_LOW_THRESHOLD,
            CONF_BATTERY_INCREASE_THRESHOLD: DEFAULT_BATTERY_INCREASE_THRESHOLD,
            CONF_ADVANCED_SETTINGS: {
                CONF_ENABLE_AUTODISCOVERY: False,
                CONF_ENABLE_REPLACED: True,
                CONF_HIDE_BATTERY_LOW: False,
                CONF_USER_LIBRARY: "",
            },
        },
    )

    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return config_entry


@pytest.fixture
def battery_device_config_entry(hass: HomeAssistant) -> ConfigEntry:
    """Fixture to create a fake device config entry with battery sensor."""
    device_config_entry = MockConfigEntry()
    device_config_entry.add_to_hass(hass)
    return device_config_entry


@pytest.fixture
def battery_device(
    device_registry: dr.DeviceRegistry, battery_device_config_entry: ConfigEntry
) -> dr.DeviceEntry:
    """Fixture to create a fake device."""
    return device_registry.async_get_or_create(
        config_entry_id=battery_device_config_entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, "AA:BB:CC:DD:EE:FF")},
        manufacturer="Fake Manufacturer",
        model="Fake Device Model",
    )


@pytest.fixture
def battery_percentage_entity_entry(
    entity_registry: er.EntityRegistry,
    battery_device_config_entry: ConfigEntry,
    battery_device: dr.DeviceEntry,
) -> er.RegistryEntry:
    """Fixture to create a battery percentage sensor entity."""
    return entity_registry.async_get_or_create(
        "sensor",
        "test",
        "unique_battery_percentage",
        config_entry=battery_device_config_entry,
        device_id=battery_device.id,
        original_name="Battery",
        unit_of_measurement="%",
        device_class="battery",
    )


@pytest.fixture
async def battery_note_subentry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    battery_device: dr.DeviceEntry,
):
    """Create a battery-note subentry for the test battery device."""
    config_entry = mock_config_entry
    initial_subentry_count = len(config_entry.subentries)

    result = await hass.config_entries.subentries.async_init(
        (config_entry.entry_id, SUBENTRY_BATTERY_NOTE),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.MENU

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: battery_device.id}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_BATTERY_TYPE: "AA",
            CONF_BATTERY_QUANTITY: 2,
            CONF_BATTERY_LOW_THRESHOLD: 10,
            CONF_ADVANCED_SETTINGS: {CONF_FILTER_OUTLIERS: False},
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(config_entry.subentries) == initial_subentry_count + 1

    await hass.async_block_till_done()

    for subentry in config_entry.subentries.values():
        if (
            subentry.subentry_type == SUBENTRY_BATTERY_NOTE
            and subentry.data.get(CONF_DEVICE_ID) == battery_device.id
        ):
            return subentry

    pytest.fail("Battery note subentry was not created")

"""Battery Notes tests configuration."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
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

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
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
        version=3,
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
async def battery_note_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    battery_device: dr.DeviceEntry,
) -> MockConfigEntry:
    """Fixture to create a Battery Notes config entry with a battery note subentry for a device."""
    mock_config_entry.create_config_subentry(
        hass,
        subentry_type=SUBENTRY_BATTERY_NOTE,
        unique_id=f"{battery_device.id}_battery_note",
        data={
            CONF_DEVICE_ID: battery_device.id,
            CONF_BATTERY_TYPE: "AA",
            CONF_BATTERY_QUANTITY: 2,
            CONF_BATTERY_LOW_THRESHOLD: 10,
            CONF_ADVANCED_SETTINGS: {
                CONF_FILTER_OUTLIERS: False,
            },
        },
    )
    await hass.async_block_till_done()
    return mock_config_entry

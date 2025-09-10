"""Test configuration for battery_notes tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant

from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_ENABLE_REPLACED,
    CONF_HIDE_BATTERY,
    CONF_ROUND_BATTERY,
    CONF_SHOW_ALL_DEVICES,
    CONF_USER_LIBRARY,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DOMAIN,
    SUBENTRY_BATTERY_NOTE,
)
from custom_components.battery_notes.coordinator import BatteryNotesDomainConfig


@pytest.fixture
def mock_config_entry():
    """Return a mock config entry."""
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.version = 1
    config_entry.minor_version = 1
    config_entry.domain = DOMAIN
    config_entry.title = "Battery Notes Test"
    config_entry.data = {}
    config_entry.options = {
        CONF_SHOW_ALL_DEVICES: False,
        CONF_HIDE_BATTERY: False,
        CONF_ROUND_BATTERY: False,
        CONF_DEFAULT_BATTERY_LOW_THRESHOLD: DEFAULT_BATTERY_LOW_THRESHOLD,
        CONF_BATTERY_INCREASE_THRESHOLD: DEFAULT_BATTERY_INCREASE_THRESHOLD,
        CONF_ADVANCED_SETTINGS: {
            CONF_ENABLE_AUTODISCOVERY: True,
            CONF_ENABLE_REPLACED: True,
            CONF_USER_LIBRARY: "",
        },
    }
    config_entry.source = "user"
    config_entry.entry_id = "test_entry_id"
    config_entry.unique_id = "test_unique_id"
    config_entry.discovery_keys = set()
    config_entry.subentries_data = {}
    # Add subentries property as an empty dict by default
    config_entry.subentries = {}
    return config_entry

@pytest.fixture
def mock_battery_subentry():
    """Return a mock battery subentry."""
    return ConfigSubentry(
        subentry_type=SUBENTRY_BATTERY_NOTE,
        subentry_id="test_subentry_id",
        title="Test Battery Device",
        data={
            CONF_DEVICE_ID: "test_device_id",
            CONF_BATTERY_TYPE: "AA",
            CONF_BATTERY_QUANTITY: 2,
        },
        unique_id="test_subentry_unique_id",
    )


@pytest.fixture
def mock_hass():
    """Return a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}

    # Mock config
    mock_config = MagicMock()
    mock_config.config_dir = "/tmp/config"
    hass.config = mock_config

    # Mock config_entries
    hass.config_entries = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock()

    return hass


@pytest.fixture
def mock_store():
    """Return a mock store."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value={})
    return store


@pytest.fixture
def mock_domain_config():
    """Return a mock domain config."""
    return BatteryNotesDomainConfig(
        enable_autodiscovery=True,
        show_all_devices=False,
        enable_replaced=True,
        hide_battery=False,
        round_battery=False,
        default_battery_low_threshold=DEFAULT_BATTERY_LOW_THRESHOLD,
        battery_increased_threshod=DEFAULT_BATTERY_INCREASE_THRESHOLD,
        user_library="",
    )

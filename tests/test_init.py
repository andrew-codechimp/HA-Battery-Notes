"""Tests for integration initialization logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.battery_notes import async_setup_entry
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_ENABLE_REPLACED,
    CONF_HIDE_BATTERY,
    CONF_HIDE_BATTERY_LOW,
    CONF_ROUND_BATTERY,
    CONF_SHOW_ALL_DEVICES,
    CONF_USER_LIBRARY,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    PLATFORMS,
)
from custom_components.battery_notes.coordinator import (
    MY_KEY,
    BatteryNotesDomainConfig,
)
from custom_components.battery_notes.library import DATA_LIBRARY


async def test_async_setup_entry_without_subentries() -> None:
    """Test async_setup_entry succeeds when there are no Battery Notes subentries."""
    # Create a mock hass with required runtime data
    mock_hass = MagicMock()
    mock_hass.data[MY_KEY] = BatteryNotesDomainConfig(store=MagicMock())
    mock_hass.data[DATA_LIBRARY] = MagicMock()
    mock_hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=None)

    # Create a simple mock config entry with required options
    mock_config_entry = MagicMock()
    mock_config_entry.entry_id = "test_entry_id"
    mock_config_entry.subentries = {}
    mock_config_entry.options = {
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
    }
    mock_config_entry.add_update_listener.return_value = lambda: None
    mock_config_entry.async_on_unload.return_value = None

    with patch("custom_components.battery_notes.async_call_later") as mock_call_later:
        result = await async_setup_entry(mock_hass, mock_config_entry)

    assert result is True
    assert mock_config_entry.runtime_data.subentry_coordinators == {}
    mock_hass.config_entries.async_forward_entry_setups.assert_called_once_with(
        mock_config_entry,
        PLATFORMS,
    )
    mock_call_later.assert_called_once()

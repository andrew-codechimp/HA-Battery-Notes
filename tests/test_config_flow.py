"""Tests for Battery Notes config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_PERCENTAGE_TEMPLATE,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_ENABLE_REPLACED,
    CONF_FILTER_OUTLIERS,
    CONF_HIDE_BATTERY,
    CONF_HIDE_BATTERY_LOW,
    CONF_NOTE,
    CONF_ROUND_BATTERY,
    CONF_SHOW_ALL_DEVICES,
    CONF_USER_LIBRARY,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DOMAIN,
    NAME as INTEGRATION_NAME,
    SUBENTRY_BATTERY_NOTE,
)

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr

if TYPE_CHECKING:
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_user_flow_setup(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,  # noqa: ARG001
) -> None:
    """Test the user flow for setting up Battery Notes integration."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == INTEGRATION_NAME
    assert result["data"] == {}
    assert result["options"] == {
        CONF_SHOW_ALL_DEVICES: False,
        CONF_HIDE_BATTERY: False,
        CONF_ROUND_BATTERY: False,
        CONF_DEFAULT_BATTERY_LOW_THRESHOLD: DEFAULT_BATTERY_LOW_THRESHOLD,
        CONF_BATTERY_INCREASE_THRESHOLD: DEFAULT_BATTERY_INCREASE_THRESHOLD,
        CONF_ADVANCED_SETTINGS: {
            CONF_ENABLE_AUTODISCOVERY: True,
            CONF_ENABLE_REPLACED: True,
            CONF_HIDE_BATTERY_LOW: False,
            CONF_USER_LIBRARY: "",
        },
    }


async def test_subentry_device_flow_creates_battery_note(
    hass: HomeAssistant,
    mock_setup_entry: AsyncMock,  # noqa: ARG001
    mock_config_entry: MockConfigEntry,
    battery_device: dr.DeviceEntry,
) -> None:
    """Test device-based subentry flow creates a battery note subentry."""
    config_entry = mock_config_entry

    # Verify config entry is loaded
    assert config_entry.state.value == "loaded"
    # Note: setup may auto-migrate existing subentries, so track the baseline
    initial_subentry_count = len(config_entry.subentries)

    # Start the subentry flow
    result = await hass.config_entries.subentries.async_init(
        (config_entry.entry_id, SUBENTRY_BATTERY_NOTE),
        context={"source": SOURCE_USER},
    )

    # First step: user menu (device or entity)
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"
    assert "device" in result["menu_options"]
    assert "entity" in result["menu_options"]

    # Choose device option
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )

    # Second step: device selection
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device"

    # Provide device input
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: battery_device.id}
    )

    # Third step: battery configuration
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"

    battery_input = {
        CONF_BATTERY_TYPE: "AA",
        CONF_BATTERY_QUANTITY: 2,
        CONF_BATTERY_LOW_THRESHOLD: 10,
        CONF_ADVANCED_SETTINGS: {
            CONF_FILTER_OUTLIERS: False,
        },
    }
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], battery_input
    )

    # Verify the subentry was created
    assert result["type"] is FlowResultType.CREATE_ENTRY
    # Should have added exactly one subentry to the baseline
    assert len(config_entry.subentries) == initial_subentry_count + 1

    expected_result_data = {
        CONF_DEVICE_ID: battery_device.id,
        CONF_BATTERY_TYPE: "AA",
        CONF_BATTERY_QUANTITY: 2,
        CONF_NOTE: "",
        CONF_BATTERY_LOW_THRESHOLD: 10,
        CONF_ADVANCED_SETTINGS: {
            CONF_BATTERY_PERCENTAGE_TEMPLATE: None,
            CONF_BATTERY_LOW_TEMPLATE: None,
            CONF_FILTER_OUTLIERS: False,
        },
    }

    assert result["data"] == expected_result_data

    # Verify the newly created subentry has the correct data
    # Find the subentry matching our battery device
    created_subentry = None
    for subentry in config_entry.subentries.values():
        if (
            subentry.subentry_type == SUBENTRY_BATTERY_NOTE
            and subentry.data.get(CONF_DEVICE_ID) == battery_device.id
        ):
            created_subentry = subentry
            break

    assert created_subentry is not None, "Battery note subentry not found for device"
    assert created_subentry.subentry_type == SUBENTRY_BATTERY_NOTE
    assert dict(created_subentry.data) == expected_result_data

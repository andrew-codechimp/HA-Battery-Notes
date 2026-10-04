"""Tests for the Battery Notes config and options flows."""

import pytest
from custom_components.battery_notes.config_flow import calc_config_attributes
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_ENABLE_REPLACED,
    CONF_HIDE_BATTERY,
    CONF_HIDE_BATTERY_LOW,
    CONF_ROUND_BATTERY,
    CONF_SHOW_ALL_DEVICES,
    CONF_SOURCE_ENTITY_ID,
    CONF_USER_LIBRARY,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


@pytest.mark.usefixtures("mock_setup_entry")
async def test_user_flow(hass: HomeAssistant) -> None:
    """Test confirmation creates an entry with the default options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] is None
    assert result["data_schema"] is None
    assert result["description_placeholders"] == {
        "documentation_url": "https://andrew-codechimp.github.io/HA-Battery-Notes/"
    }

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Battery Notes"
    assert result["data"] == {}
    assert result["options"] == {
        CONF_SHOW_ALL_DEVICES: False,
        CONF_HIDE_BATTERY: False,
        CONF_ROUND_BATTERY: False,
        CONF_DEFAULT_BATTERY_LOW_THRESHOLD: 10,
        CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD: 25,
        CONF_ADVANCED_SETTINGS: {
            CONF_ENABLE_AUTODISCOVERY: True,
            CONF_ENABLE_REPLACED: True,
            CONF_HIDE_BATTERY_LOW: False,
            CONF_USER_LIBRARY: "",
        },
    }


async def test_user_already_configured(hass: HomeAssistant) -> None:
    """Test an existing entry prevents a second user flow."""
    MockConfigEntry(domain=DOMAIN, title="Renamed Battery Notes", data={}).add_to_hass(
        hass
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_suggested_values(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test saved options are suggested in the form and advanced settings."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert result["errors"] is None

    schema = result["data_schema"].schema.copy()
    advanced_schema = schema.pop(CONF_ADVANCED_SETTINGS).schema.schema
    expected_options = dict(mock_config_entry.options)
    expected_advanced_options = expected_options.pop(CONF_ADVANCED_SETTINGS)

    assert {
        key.schema: key.description["suggested_value"] for key in schema
    } == expected_options
    assert {
        key.schema: key.description["suggested_value"] for key in advanced_schema
    } == expected_advanced_options


@pytest.mark.parametrize(
    ("enabled", "thresholds", "user_library"),
    [
        pytest.param(True, (0, 99), "custom_battery_library.json", id="enable"),
        pytest.param(False, (99, 0), "", id="disable"),
    ],
)
async def test_options(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    enabled: bool,
    thresholds: tuple[int, int],
    user_library: str,
) -> None:
    """Test updating all options while preserving the entry title and data."""
    low_threshold, increase_threshold = thresholds
    mock_config_entry.add_to_hass(hass)
    initial_options = {
        CONF_SHOW_ALL_DEVICES: not enabled,
        CONF_HIDE_BATTERY: not enabled,
        CONF_ROUND_BATTERY: not enabled,
        CONF_DEFAULT_BATTERY_LOW_THRESHOLD: 10,
        CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD: 25,
        CONF_ADVANCED_SETTINGS: {
            CONF_ENABLE_AUTODISCOVERY: not enabled,
            CONF_ENABLE_REPLACED: not enabled,
            CONF_HIDE_BATTERY_LOW: not enabled,
            CONF_USER_LIBRARY: "previous_library.json",
        },
    }
    hass.config_entries.async_update_entry(mock_config_entry, options=initial_options)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    options = {
        CONF_SHOW_ALL_DEVICES: enabled,
        CONF_HIDE_BATTERY: enabled,
        CONF_ROUND_BATTERY: enabled,
        CONF_DEFAULT_BATTERY_LOW_THRESHOLD: low_threshold,
        CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD: increase_threshold,
        CONF_ADVANCED_SETTINGS: {
            CONF_ENABLE_AUTODISCOVERY: enabled,
            CONF_ENABLE_REPLACED: enabled,
            CONF_HIDE_BATTERY_LOW: enabled,
            CONF_USER_LIBRARY: user_library,
        },
    }
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=options
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == options
    assert mock_config_entry.options == options
    assert mock_config_entry.title == "Battery Notes"
    assert mock_config_entry.data == {}


async def test_user_already_configured_on_confirm(hass: HomeAssistant) -> None:
    """Test an entry added while the form is open prevents a duplicate."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    MockConfigEntry(domain=DOMAIN, data={}).add_to_hass(hass)

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


def test_unregistered_entity_attributes(hass: HomeAssistant) -> None:
    """Test the object ID identifies an unregistered entity with a supplied title."""
    assert calc_config_attributes(
        hass,
        {
            CONF_SOURCE_ENTITY_ID: "sensor.unregistered_battery",
            CONF_NAME: "Unregistered battery",
        },
    ) == ("bn_unregistered_battery", "Unregistered battery")

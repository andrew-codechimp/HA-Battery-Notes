"""Battery Notes tests configuration."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
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
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

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
        domain="battery_notes",
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

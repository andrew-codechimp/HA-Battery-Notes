"""Fixtures for Battery Notes tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
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
    CONF_USER_LIBRARY,
    DOMAIN,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in Home Assistant."""


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Override async_setup_entry."""
    with patch(
        "custom_components.battery_notes.async_setup_entry", return_value=True
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a Battery Notes entry with default options."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Battery Notes",
        version=4,
        data={},
        options={
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
        },
    )

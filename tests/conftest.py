"""Fixtures for Battery Notes tests."""

from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

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
from custom_components.battery_notes.library import DATA_LIBRARY, Library
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from homeassistant.core import HomeAssistant


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


@pytest.fixture
def _mock_library_file() -> Generator[MagicMock]:
    """Provide a fixed library JSON file through the normal file reader."""
    with patch(
        "custom_components.battery_notes.library.open",
        mock_open(read_data=load_fixture("library.json")),
    ) as library_file:
        yield library_file


@pytest.fixture
def battery_library(hass: HomeAssistant, _mock_library_file: MagicMock) -> Library:
    """Register a real library backed by fixture data."""
    library = Library(hass)
    hass.data[DATA_LIBRARY] = library
    return library


@pytest.fixture
async def loaded_library(battery_library: Library) -> Library:
    """Load fixture data through the public library API."""
    await battery_library.load_libraries()
    assert battery_library.is_loaded
    return battery_library

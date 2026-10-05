"""Tests for loading and unloading the Battery Notes integration."""

from collections.abc import Generator
from copy import deepcopy
from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from custom_components.battery_notes import DISCOVERY_DELAY
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
from custom_components.battery_notes.coordinator import MY_KEY
from custom_components.battery_notes.library import DATA_LIBRARY, Library
from custom_components.battery_notes.store import (
    BatteryNotesStorage,
    async_get_registry,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

CUSTOM_OPTIONS = {
    CONF_SHOW_ALL_DEVICES: True,
    CONF_HIDE_BATTERY: True,
    CONF_ROUND_BATTERY: True,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD: 15,
    CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD: 30,
    CONF_ADVANCED_SETTINGS: {
        CONF_ENABLE_AUTODISCOVERY: False,
        CONF_ENABLE_REPLACED: False,
        CONF_HIDE_BATTERY_LOW: True,
        CONF_USER_LIBRARY: "custom_library.json",
    },
}


@pytest.fixture
def mock_discovery_manager() -> Generator[MagicMock]:
    """Observe when setup starts discovery."""
    with patch(
        "custom_components.battery_notes.DiscoveryManager", autospec=True
    ) as manager:
        yield manager.return_value


@pytest.mark.parametrize(
    "mock_config_entry",
    [
        pytest.param({}, id="default-options"),
        pytest.param(CUSTOM_OPTIONS, id="custom-options"),
    ],
    indirect=True,
)
async def test_setup_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the parent loads its options, storage, library, and services."""
    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    runtime_data = mock_config_entry.runtime_data
    assert runtime_data.domain_config is hass.data[MY_KEY]
    assert isinstance(runtime_data.store, BatteryNotesStorage)
    assert runtime_data.store is await async_get_registry(hass)
    assert runtime_data.loaded_subentries == {}
    assert runtime_data.subentry_coordinators == {}
    assert isinstance(hass.data[DATA_LIBRARY], Library)
    assert not hass.data[DATA_LIBRARY].is_loaded

    config = vars(runtime_data.domain_config).copy()
    assert config.pop("store") is runtime_data.store
    assert {
        "config": config,
        "services": sorted(hass.services.async_services()[DOMAIN]),
    } == snapshot


@pytest.mark.parametrize(
    "mock_config_entry",
    [
        pytest.param({}, id="discovery-enabled"),
        pytest.param(
            {CONF_ADVANCED_SETTINGS: {CONF_ENABLE_AUTODISCOVERY: False}},
            id="discovery-disabled",
        ),
    ],
    indirect=True,
)
async def test_delayed_discovery(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_library_updater: MagicMock,
    mock_discovery_manager: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test loading the library is delayed and discovery follows the saved option."""
    await setup_integration(hass, mock_config_entry)

    freezer.tick(timedelta(seconds=DISCOVERY_DELAY - 1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    mock_library_updater.get_library_updates.assert_not_awaited()
    mock_discovery_manager.start_discovery.assert_not_awaited()
    assert not hass.data[DATA_LIBRARY].is_loaded

    freezer.tick(timedelta(seconds=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()

    mock_library_updater.copy_schema.assert_awaited_once_with()
    mock_library_updater.get_library_updates.assert_awaited_once_with(startup=True)
    assert hass.data[DATA_LIBRARY].is_loaded
    assert mock_discovery_manager.start_discovery.await_count == int(
        mock_config_entry.options[CONF_ADVANCED_SETTINGS][CONF_ENABLE_AUTODISCOVERY]
    )


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param("async_unload", id="unload"),
        pytest.param("async_remove", id="remove"),
    ],
)
async def test_load_unload_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_library_updater: MagicMock,
    freezer: FrozenDateTimeFactory,
    operation: str,
) -> None:
    """Test unloading or removing the parent cancels its update and discovery work."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_library_updater.async_start_daily_update.assert_called_once_with()

    assert await getattr(hass.config_entries, operation)(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_library_updater.async_start_daily_update.return_value.assert_called_once_with()

    freezer.tick(timedelta(seconds=DISCOVERY_DELAY))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    mock_library_updater.copy_schema.assert_not_awaited()
    mock_library_updater.get_library_updates.assert_not_awaited()


async def test_update_options(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_library_updater: MagicMock,
    snapshot: SnapshotAssertion,
) -> None:
    """Test options changes reload the parent and preserve shared storage and library."""
    await setup_integration(hass, mock_config_entry)
    old_runtime_data = mock_config_entry.runtime_data
    library = hass.data[DATA_LIBRARY]

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=deepcopy(CUSTOM_OPTIONS)
    )
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.options == CUSTOM_OPTIONS
    assert mock_config_entry.runtime_data is not old_runtime_data
    assert mock_config_entry.runtime_data.store is old_runtime_data.store
    assert hass.data[DATA_LIBRARY] is library
    assert mock_library_updater.async_start_daily_update.call_count == 2
    mock_library_updater.async_start_daily_update.return_value.assert_called_once_with()

    config = vars(mock_config_entry.runtime_data.domain_config).copy()
    assert config.pop("store") is old_runtime_data.store
    assert config == snapshot


async def test_update_options_clear_user_library(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test clearing the user library, which omits it from the options, reloads."""
    await setup_integration(hass, mock_config_entry)
    options = deepcopy(CUSTOM_OPTIONS)
    del options[CONF_ADVANCED_SETTINGS][CONF_USER_LIBRARY]

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=options
    )
    await hass.async_block_till_done()

    assert CONF_USER_LIBRARY not in mock_config_entry.options[CONF_ADVANCED_SETTINGS]
    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data.domain_config.user_library == ""

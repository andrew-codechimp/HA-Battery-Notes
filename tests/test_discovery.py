"""Tests for discovery with the real battery library and config flow."""

from collections.abc import Generator
from types import MappingProxyType
from unittest.mock import AsyncMock, patch

import pytest
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    DOMAIN,
    SUBENTRY_BATTERY_NOTE,
)
from custom_components.battery_notes.coordinator import MY_KEY, BatteryNotesDomainConfig
from custom_components.battery_notes.discovery import DiscoveryManager
from custom_components.battery_notes.library import Library, ModelInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture
from syrupy.assertion import SnapshotAssertion

from homeassistant.config_entries import (
    SOURCE_IGNORE,
    SOURCE_INTEGRATION_DISCOVERY,
    ConfigFlowResult,
    ConfigSubentry,
)
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.util import dt as dt_util


@pytest.fixture(autouse=True)
def mock_library_download() -> Generator[AsyncMock]:
    """Keep library downloads independent of the network."""
    with patch(
        "custom_components.battery_notes.library_updater.LibraryUpdaterClient.async_get_data",
        return_value=load_fixture("library.json"),
    ) as download:
        yield download


@pytest.fixture
def source_config_entry(
    hass: HomeAssistant, request: pytest.FixtureRequest
) -> MockConfigEntry:
    """Register the integration owning the discovered device."""
    entry = MockConfigEntry(domain=getattr(request, "param", "mqtt"))
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def source_device(
    device_registry: dr.DeviceRegistry,
    source_config_entry: MockConfigEntry,
    request: pytest.FixtureRequest,
) -> dr.DeviceEntry:
    """Register a device whose model is matched against the fixture library."""
    model_info = getattr(
        request, "param", ModelInfo("LUMI", "lumi.sensor_magnet.aq2", None, None)
    )
    return device_registry.async_get_or_create(
        config_entry_id=source_config_entry.entry_id,
        identifiers={(source_config_entry.domain, "source-device")},
        name="Front door",
        manufacturer=model_info.manufacturer,
        model=model_info.model,
        model_id=model_info.model_id,
        hw_version=model_info.hw_version,
    )


@pytest.fixture
def discovery_manager(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    battery_library: Library,
) -> DiscoveryManager:
    """Configure discovery with an unloaded real library and a parent entry."""
    assert not battery_library.is_loaded
    mock_config_entry.add_to_hass(hass)
    config = BatteryNotesDomainConfig(library_last_update=dt_util.utcnow())
    hass.data[MY_KEY] = config
    return DiscoveryManager(hass, config)


@pytest.fixture
async def discovered_flow(
    hass: HomeAssistant,
    discovery_manager: DiscoveryManager,
    source_device: dr.DeviceEntry,
) -> ConfigFlowResult:
    """Scan registered devices and return the resulting confirmation form."""
    await discovery_manager.start_discovery()
    await hass.async_block_till_done(wait_background_tasks=True)

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_INTEGRATION_DISCOVERY
    assert flows[0]["context"]["unique_id"] == f"bn_{source_device.id}"
    assert flows[0]["context"]["title_placeholders"]["name"] == "Front door - MQTT"
    return await hass.config_entries.flow.async_configure(flows[0]["flow_id"])


@pytest.mark.parametrize(
    ("source_device", "expected_battery"),
    [
        pytest.param(
            ModelInfo("Mi", "MS009", None, None), ("CR2540", 1), id="model-only"
        ),
        pytest.param(
            ModelInfo("Aqara", "Roller shade driver E1", "ZNJLBL01LM", None),
            ("Rechargeable", 1),
            id="model-id",
        ),
        pytest.param(
            ModelInfo("Google", "Topaz-2.7", None, "Battery"),
            ("AA", 6),
            id="battery-hardware",
        ),
        pytest.param(
            ModelInfo("Google", "Topaz-2.7", None, "Wired"),
            ("AA", 3),
            id="wired-hardware",
        ),
        pytest.param(
            ModelInfo("eQ-3", "HmIP-WGC", None, "Unknown"),
            ("AA", 2),
            id="generic-fallback",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Specific sensor", "S1", "Rev2"),
            ("CR2032", 4),
            id="full-match",
        ),
    ],
    indirect=["source_device"],
)
async def test_matching_device_discovered(
    discovered_flow: ConfigFlowResult, expected_battery: tuple[str, int]
) -> None:
    """Test library matches produce a discovery form with correct battery suggestions."""
    assert discovered_flow["type"] is FlowResultType.FORM
    assert discovered_flow["step_id"] == "battery"
    assert discovered_flow["errors"] == {}
    defaults = discovered_flow["data_schema"]({CONF_ADVANCED_SETTINGS: {}})
    assert (
        defaults[CONF_BATTERY_TYPE],
        defaults[CONF_BATTERY_QUANTITY],
    ) == expected_battery


@pytest.mark.parametrize(
    "source_device",
    [
        pytest.param(
            ModelInfo("Unknown", "Unknown sensor", None, None),
            id="unknown-manufacturer",
        ),
        pytest.param(ModelInfo("Mi", "Unknown sensor", None, None), id="unknown-model"),
        pytest.param(
            ModelInfo("Aqara", "Roller shade driver E1", None, None),
            id="missing-model-id",
        ),
        pytest.param(
            ModelInfo("Meross", "Smart Presence Sensor", "Wrong model ID", None),
            id="wrong-model-id",
        ),
        pytest.param(
            ModelInfo("Google", "Topaz-2.7", None, "Unknown"), id="wrong-hardware"
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Ambiguous sensor", None, None),
            id="ambiguous",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Manual sensor", None, None), id="manual"
        ),
    ],
    indirect=True,
)
@pytest.mark.usefixtures("source_device")
async def test_device_not_discovered(
    hass: HomeAssistant,
    discovery_manager: DiscoveryManager,
    battery_library: Library,
) -> None:
    """Test unmatched, ambiguous, and manual definitions create no automatic flow."""
    await discovery_manager.start_discovery()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert battery_library.is_loaded
    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []


async def test_discovery_creates_subentry(
    hass: HomeAssistant,
    discovered_flow: ConfigFlowResult,
    mock_config_entry: MockConfigEntry,
    source_device: dr.DeviceEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test confirming a scanned device adds a note with no discovery-only metadata."""
    user_input = discovered_flow["data_schema"]({CONF_ADVANCED_SETTINGS: {}})
    result = await hass.config_entries.flow.async_configure(
        discovered_flow["flow_id"], user_input
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "created_sub_entry"
    assert len(mock_config_entry.subentries) == 1
    subentry = next(iter(mock_config_entry.subentries.values()))
    assert subentry.title == "Front door"
    assert subentry.unique_id == f"bn_{source_device.id}"
    assert subentry.subentry_type == SUBENTRY_BATTERY_NOTE
    data = dict(subentry.data)
    assert data.pop(CONF_DEVICE_ID) == source_device.id
    assert data == snapshot
    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_rescan_pending_discovery(
    hass: HomeAssistant,
    discovered_flow: ConfigFlowResult,
    discovery_manager: DiscoveryManager,
) -> None:
    """Test rescanning a device keeps the existing discovery flow."""
    await discovery_manager.start_discovery()
    await hass.async_block_till_done(wait_background_tasks=True)

    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert len(flows) == 1
    assert flows[0]["flow_id"] == discovered_flow["flow_id"]


async def test_configured_device_not_discovered(
    hass: HomeAssistant,
    discovery_manager: DiscoveryManager,
    mock_config_entry: MockConfigEntry,
    source_device: dr.DeviceEntry,
) -> None:
    """Test existing device notes are excluded from the scan."""
    hass.config_entries.async_add_subentry(
        mock_config_entry,
        ConfigSubentry(
            data=MappingProxyType({CONF_DEVICE_ID: source_device.id}),
            title="Existing note",
            subentry_type=SUBENTRY_BATTERY_NOTE,
            unique_id=f"bn_{source_device.id}",
        ),
    )
    await discovery_manager.start_discovery()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []


async def test_ignored_device_not_discovered(
    hass: HomeAssistant,
    discovery_manager: DiscoveryManager,
    source_device: dr.DeviceEntry,
) -> None:
    """Test a device with an ignored discovery is not offered again."""
    MockConfigEntry(
        domain=DOMAIN,
        source=SOURCE_IGNORE,
        unique_id=f"bn_{source_device.id}",
        data={},
    ).add_to_hass(hass)

    await discovery_manager.start_discovery()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []


@pytest.mark.parametrize("source_config_entry", ["unifi"], indirect=True)
@pytest.mark.usefixtures("source_device")
async def test_ignored_integration_not_discovered(
    hass: HomeAssistant,
    discovery_manager: DiscoveryManager,
) -> None:
    """Test library ignored domains suppress otherwise matching devices."""
    await discovery_manager.start_discovery()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []


async def test_disabled_device_not_discovered(
    hass: HomeAssistant,
    discovery_manager: DiscoveryManager,
    source_device: dr.DeviceEntry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test disabled devices are not offered for discovery."""
    device_registry.async_update_device(
        source_device.id, disabled_by=dr.DeviceEntryDisabler.USER
    )
    await discovery_manager.start_discovery()
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.config_entries.flow.async_progress_by_handler(DOMAIN) == []


async def test_parent_removed_before_confirmation(
    hass: HomeAssistant,
    discovered_flow: ConfigFlowResult,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test removal of the parent while confirmation is open aborts the flow."""
    await hass.config_entries.async_remove(mock_config_entry.entry_id)

    result = await hass.config_entries.flow.async_configure(
        discovered_flow["flow_id"],
        discovered_flow["data_schema"]({CONF_ADVANCED_SETTINGS: {}}),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "integration_not_added"

"""Tests for the Battery Notes discovery config flow."""

from collections.abc import Generator
from types import MappingProxyType
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEVICE_NAME,
    CONF_HW_VERSION,
    CONF_INTEGRATION_NAME,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_MODEL_ID,
    CONF_RETAIN_STATE,
    DOMAIN,
    SUBENTRY_BATTERY_NOTE,
)
from custom_components.battery_notes.coordinator import MY_KEY, BatteryNotesDomainConfig
from custom_components.battery_notes.library import (
    DATA_LIBRARY,
    DeviceBatteryDetails,
    Library,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion

from homeassistant.config_entries import (
    SOURCE_IGNORE,
    SOURCE_INTEGRATION_DISCOVERY,
    ConfigEntryDisabler,
    ConfigFlowResult,
    ConfigSubentry,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr


@pytest.fixture(autouse=True)
def mock_library(hass: HomeAssistant, request: pytest.FixtureRequest) -> MagicMock:
    """Provide deterministic battery suggestions without reading library files."""
    library = create_autospec(Library, instance=True)
    library.is_loaded = getattr(request, "param", True)
    library.get_device_battery_details.return_value = DeviceBatteryDetails(
        "Test Manufacturer", "Door sensor", None, None, "AA", 2
    )
    hass.data[DATA_LIBRARY] = library
    return library


@pytest.fixture(autouse=True)
def mock_library_updater(request: pytest.FixtureRequest) -> Generator[MagicMock]:
    """Keep library refreshes independent of the network."""
    with patch(
        "custom_components.battery_notes.config_flow.LibraryUpdater", autospec=True
    ) as updater:
        updater.return_value.time_to_update_library.return_value = getattr(
            request, "param", False
        )
        yield updater.return_value


@pytest.fixture
def parent_entry(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Register the parent without loading its platforms."""
    mock_config_entry.add_to_hass(hass)
    return mock_config_entry


@pytest.fixture
def discovery_info(battery_note_device: dr.DeviceEntry) -> dict[str, str | None]:
    """Provide the data supplied by integration discovery."""
    return {
        CONF_DEVICE_ID: battery_note_device.id,
        CONF_DEVICE_NAME: battery_note_device.name,
        CONF_INTEGRATION_NAME: "Test integration",
        CONF_MANUFACTURER: battery_note_device.manufacturer,
        CONF_MODEL: battery_note_device.model,
        CONF_MODEL_ID: battery_note_device.model_id,
        CONF_HW_VERSION: battery_note_device.hw_version,
    }


@pytest.fixture
async def discovered_flow(
    hass: HomeAssistant,
    parent_entry: MockConfigEntry,
    discovery_info: dict[str, str | None],
) -> ConfigFlowResult:
    """Start discovery and return its battery confirmation form."""
    assert hass.config_entries.async_get_entry(parent_entry.entry_id) is parent_entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data=discovery_info,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"
    return result


@pytest.fixture(
    params=[
        pytest.param("missing", id="missing"),
        pytest.param("ignored", id="ignored"),
        pytest.param("disabled", id="disabled"),
    ]
)
def unavailable_parent(hass: HomeAssistant, request: pytest.FixtureRequest) -> None:
    """Optionally register an entry excluded from integration discovery."""
    if request.param == "missing":
        return
    entry = MockConfigEntry(
        domain=DOMAIN,
        source={"ignored": SOURCE_IGNORE, "disabled": "user"}[request.param],
        disabled_by={"ignored": None, "disabled": ConfigEntryDisabler.USER}[
            request.param
        ],
    )
    entry.add_to_hass(hass)


@pytest.mark.usefixtures("unavailable_parent")
async def test_discovery_without_parent(
    hass: HomeAssistant, discovery_info: dict[str, str | None]
) -> None:
    """Test discovery requires an enabled parent integration entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "integration_not_added"


@pytest.mark.parametrize(
    ("integration_name", "expected_name"),
    [
        pytest.param("Test integration", "Door sensor - Test integration", id="named"),
        pytest.param("", "Door sensor", id="unnamed"),
    ],
)
@pytest.mark.usefixtures("parent_entry")
async def test_discovery_title(
    hass: HomeAssistant,
    discovery_info: dict[str, str | None],
    integration_name: str,
    expected_name: str,
) -> None:
    """Test the discovery title includes an integration name when supplied."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data={**discovery_info, CONF_INTEGRATION_NAME: integration_name},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"
    flow = hass.config_entries.flow.async_progress_by_handler(DOMAIN)[0]
    assert flow["context"]["title_placeholders"]["name"] == expected_name


async def test_discovery_already_configured(
    hass: HomeAssistant,
    parent_entry: MockConfigEntry,
    discovery_info: dict[str, str | None],
) -> None:
    """Test discovery skips unrelated notes and aborts for a matching saved note."""
    for device_id in ("other-device", discovery_info[CONF_DEVICE_ID]):
        hass.config_entries.async_add_subentry(
            parent_entry,
            ConfigSubentry(
                data=MappingProxyType({CONF_DEVICE_ID: device_id}),
                title="Saved battery note",
                subentry_type=SUBENTRY_BATTERY_NOTE,
                unique_id=f"bn_{device_id}",
            ),
        )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data=discovery_info,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(parent_entry.subentries) == 2


@pytest.mark.parametrize(
    ("mock_library", "mock_library_updater"),
    [
        pytest.param(True, False, id="current-library"),
        pytest.param(False, True, id="refresh-library"),
    ],
    indirect=True,
)
async def test_discovery_library_loading(
    discovered_flow: ConfigFlowResult,
    mock_library: MagicMock,
    mock_library_updater: MagicMock,
) -> None:
    """Test discovery refreshes and loads the library when necessary."""
    assert discovered_flow["errors"] == {}
    mock_library_updater.time_to_update_library.assert_awaited_once_with(1)
    assert mock_library_updater.get_library_updates.await_count == int(
        mock_library_updater.time_to_update_library.return_value
    )
    assert mock_library.load_libraries.await_count == int(not mock_library.is_loaded)
    defaults = discovered_flow["data_schema"]({CONF_ADVANCED_SETTINGS: {}})
    assert defaults[CONF_BATTERY_TYPE] == "AA"
    assert defaults[CONF_BATTERY_QUANTITY] == 2


@pytest.mark.parametrize(
    "battery_details",
    [
        pytest.param(None, id="unknown-model"),
        pytest.param(
            DeviceBatteryDetails(
                "Test Manufacturer", "Door sensor", None, None, "Manual", 1
            ),
            id="manual-model",
        ),
    ],
)
@pytest.mark.usefixtures("parent_entry")
async def test_discovery_manual_configuration(
    hass: HomeAssistant,
    discovery_info: dict[str, str | None],
    mock_library: MagicMock,
    battery_details: DeviceBatteryDetails | None,
) -> None:
    """Test unmatched and manual library models accept user-supplied battery details."""
    mock_library.get_device_battery_details.return_value = battery_details
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data=discovery_info,
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"
    defaults = result["data_schema"](
        {CONF_BATTERY_TYPE: "AAA", CONF_ADVANCED_SETTINGS: {}}
    )
    assert defaults[CONF_BATTERY_QUANTITY] == 1

    result = await hass.config_entries.flow.async_configure(result["flow_id"], defaults)
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "created_sub_entry"


async def test_discovery_with_other_note(
    hass: HomeAssistant,
    parent_entry: MockConfigEntry,
    discovery_info: dict[str, str | None],
) -> None:
    """Test an existing note for another device does not prevent discovery."""
    hass.config_entries.async_add_subentry(
        parent_entry,
        ConfigSubentry(
            data=MappingProxyType({CONF_DEVICE_ID: "other-device"}),
            title="Other battery note",
            subentry_type=SUBENTRY_BATTERY_NOTE,
            unique_id="bn_other-device",
        ),
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data=discovery_info,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], result["data_schema"]({CONF_ADVANCED_SETTINGS: {}})
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "created_sub_entry"
    assert len(parent_entry.subentries) == 2


@pytest.mark.parametrize(
    "show_all_devices",
    [pytest.param(False, id="battery-devices"), pytest.param(True, id="all-devices")],
)
async def test_device_form(
    hass: HomeAssistant, show_all_devices: bool, snapshot: SnapshotAssertion
) -> None:
    """Test the parent device form follows the device-filtering option."""
    hass.data[MY_KEY] = BatteryNotesDomainConfig(show_all_devices=show_all_devices)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "device"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device"
    assert result["data_schema"].schema[CONF_DEVICE_ID].config == snapshot


async def test_device_without_parent(
    hass: HomeAssistant, battery_note_device: dr.DeviceEntry
) -> None:
    """Test the device step aborts if the parent is absent when selection is submitted."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "device"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_DEVICE_ID: battery_note_device.id}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "integration_not_added"


@pytest.mark.usefixtures("parent_entry")
async def test_discovery_device_without_model(
    hass: HomeAssistant,
    battery_note_device: dr.DeviceEntry,
    mock_library: MagicMock,
) -> None:
    """Test devices without model details can be configured without a library lookup."""
    dr.async_get(hass).async_update_device(
        battery_note_device.id, manufacturer=None, model=None
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "device"},
        data={CONF_DEVICE_ID: battery_note_device.id},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"
    assert result["description_placeholders"] == {
        "name": "Door sensor",
        "manufacturer": "",
        "model": "",
        "model_id": "",
        "hw_version": "",
    }
    mock_library.get_device_battery_details.assert_not_awaited()


async def test_discovery_updates_advanced_settings(
    hass: HomeAssistant,
    parent_entry: MockConfigEntry,
    discovery_info: dict[str, str | None],
) -> None:
    """Test confirmation overrides advanced settings supplied with discovery."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_INTEGRATION_DISCOVERY},
        data={
            **discovery_info,
            CONF_NAME: "Front door battery",
            CONF_ADVANCED_SETTINGS: {CONF_RETAIN_STATE: True},
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], result["data_schema"]({CONF_ADVANCED_SETTINGS: {}})
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "created_sub_entry"
    subentry = next(iter(parent_entry.subentries.values()))
    assert subentry.title == "Front door battery"
    assert subentry.data[CONF_ADVANCED_SETTINGS][CONF_RETAIN_STATE] is False

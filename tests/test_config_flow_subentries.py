"""Tests for Battery Notes subentry config flows."""

from collections.abc import Generator
from copy import deepcopy
from types import MappingProxyType
from unittest.mock import MagicMock, create_autospec, patch

import pytest
from custom_components.battery_notes.config_flow import calc_config_attributes
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_PERCENTAGE_TEMPLATE,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_FILTER_OUTLIERS,
    CONF_NOTE,
    CONF_RETAIN_STATE,
    CONF_SOURCE_ENTITY_ID,
    SUBENTRY_BATTERY_NOTE,
)
from custom_components.battery_notes.coordinator import MY_KEY, BatteryNotesDomainConfig
from custom_components.battery_notes.library import (
    DATA_LIBRARY,
    DeviceBatteryDetails,
    Library,
    ModelInfo,
)
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    get_schema_suggested_value,
)
from syrupy.assertion import SnapshotAssertion

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import SOURCE_USER, ConfigSubentry, SubentryFlowResult
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, entity_registry as er

BATTERY_INPUT = {
    CONF_BATTERY_TYPE: "CR2032",
    CONF_BATTERY_QUANTITY: 2.0,
    CONF_BATTERY_LOW_THRESHOLD: 15.0,
    CONF_BATTERY_INCREASE_THRESHOLD: 30.0,
    CONF_NOTE: "Under the cover",
    CONF_ADVANCED_SETTINGS: {
        CONF_BATTERY_PERCENTAGE_TEMPLATE: "{{ 50 }}",
        CONF_BATTERY_LOW_TEMPLATE: "{{ false }}",
        CONF_RETAIN_STATE: True,
        CONF_FILTER_OUTLIERS: True,
    },
}


@pytest.fixture(autouse=True)
def add_config_entry(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Register the parent entry without setting up its platforms."""
    mock_config_entry.add_to_hass(hass)


@pytest.fixture(autouse=True)
def mock_library(hass: HomeAssistant, request: pytest.FixtureRequest) -> MagicMock:
    """Mock library lookups without reading library files."""
    library = create_autospec(Library, instance=True)
    library.is_loaded = getattr(request, "param", True)
    library.get_device_battery_details.return_value = DeviceBatteryDetails(
        "Acme", "Motion sensor", "MS1", "1.0", "AA", 3
    )
    hass.data[DATA_LIBRARY] = library
    return library


@pytest.fixture(autouse=True)
def mock_library_updater(request: pytest.FixtureRequest) -> Generator[MagicMock]:
    """Mock library updates to keep flows independent of the network."""
    with patch(
        "custom_components.battery_notes.config_flow.LibraryUpdater", autospec=True
    ) as updater:
        updater.return_value.time_to_update_library.return_value = getattr(
            request, "param", False
        )
        yield updater.return_value


@pytest.fixture
def source_device(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> dr.DeviceEntry:
    """Create a source device owned by another integration."""
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("test", "motion-sensor")},
        name="Motion sensor",
        manufacturer="Acme",
        model="Motion sensor",
        model_id="MS1",
        hw_version="1.0",
    )
    return device_registry.async_update_device(device.id, name_by_user="Hall motion")


@pytest.fixture
def source_entity(
    entity_registry: er.EntityRegistry, source_device: dr.DeviceEntry
) -> er.RegistryEntry:
    """Create a registered battery entity on the source device."""
    return entity_registry.async_get_or_create(
        "sensor",
        "test",
        "motion-battery",
        device_id=source_device.id,
        original_name="Battery",
        original_device_class=SensorDeviceClass.BATTERY,
    )


@pytest.fixture(
    params=[pytest.param("device", id="device"), pytest.param("entity", id="entity")]
)
def source_step(request: pytest.FixtureRequest) -> str:
    """Exercise both ways of selecting a battery note source."""
    return request.param


@pytest.fixture
def selection_input(
    source_step: str, source_device: dr.DeviceEntry, source_entity: er.RegistryEntry
) -> dict[str, str]:
    """Return the source selection for the current flow."""
    return {
        "device": {CONF_DEVICE_ID: source_device.id},
        "entity": {CONF_SOURCE_ENTITY_ID: source_entity.entity_id},
    }[source_step]


@pytest.fixture
async def source_form(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, source_step: str
) -> SubentryFlowResult:
    """Start a user flow and select its device or entity menu item."""
    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, SUBENTRY_BATTERY_NOTE),
        context={"source": SOURCE_USER},
    )
    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "user"
    assert result["menu_options"] == ["device", "entity"]
    assert result["description_placeholders"] == {
        "documentation_url": "https://andrew-codechimp.github.io/HA-Battery-Notes/"
    }

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": source_step}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == source_step
    assert result["errors"] == {}
    return result


@pytest.fixture
def mock_subentry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    source_device: dr.DeviceEntry,
    source_entity: er.RegistryEntry,
) -> ConfigSubentry:
    """Add an existing battery note for reconfiguration."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                **deepcopy(BATTERY_INPUT),
                CONF_BATTERY_QUANTITY: 2,
                CONF_BATTERY_LOW_THRESHOLD: 15,
                CONF_BATTERY_INCREASE_THRESHOLD: 30,
                CONF_DEVICE_ID: source_device.id,
                CONF_SOURCE_ENTITY_ID: source_entity.entity_id,
            }
        ),
        subentry_type=SUBENTRY_BATTERY_NOTE,
        title="Hall battery",
        unique_id=f"bn_{source_entity.unique_id}",
    )
    hass.config_entries.async_add_subentry(mock_config_entry, subentry)
    return subentry


@pytest.mark.parametrize(
    "show_all_devices",
    [pytest.param(False, id="battery-devices"), pytest.param(True, id="all-devices")],
)
async def test_device_selector(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    show_all_devices: bool,
    snapshot: SnapshotAssertion,
) -> None:
    """Test the device selector follows the show-all-devices setting."""
    hass.data[MY_KEY] = BatteryNotesDomainConfig(show_all_devices=show_all_devices)
    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, SUBENTRY_BATTERY_NOTE),
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "device"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "device"
    assert result["data_schema"].schema[CONF_DEVICE_ID].config == snapshot


async def test_create_subentry(
    hass: HomeAssistant,
    source_form: SubentryFlowResult,
    selection_input: dict[str, str],
    mock_config_entry: MockConfigEntry,
    source_device: dr.DeviceEntry,
) -> None:
    """Test library suggestions and saving a named note with custom battery details."""
    result = await hass.config_entries.subentries.async_configure(
        source_form["flow_id"], {**selection_input, CONF_NAME: "Front door battery"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"
    assert result["errors"] == {}
    assert result["description_placeholders"] == {
        "name": "Front door battery",
        "manufacturer": "Acme",
        "model": "Motion sensor",
        "model_id": "MS1",
        "hw_version": "1.0",
    }
    defaults = result["data_schema"]({CONF_ADVANCED_SETTINGS: {}})
    assert defaults[CONF_BATTERY_TYPE] == "AA"
    assert defaults[CONF_BATTERY_QUANTITY] == 3
    assert defaults[CONF_BATTERY_LOW_THRESHOLD] == 0
    assert defaults[CONF_BATTERY_INCREASE_THRESHOLD] == 0

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], deepcopy(BATTERY_INPUT)
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Front door battery"
    assert result["data"] == {
        **BATTERY_INPUT,
        **selection_input,
        CONF_DEVICE_ID: source_device.id,
    }
    for key in (
        CONF_BATTERY_QUANTITY,
        CONF_BATTERY_LOW_THRESHOLD,
        CONF_BATTERY_INCREASE_THRESHOLD,
    ):
        assert isinstance(result["data"][key], int)
    subentry = next(iter(mock_config_entry.subentries.values()))
    assert subentry.title == result["title"]
    assert subentry.data == result["data"]
    assert subentry.subentry_type == SUBENTRY_BATTERY_NOTE
    assert (
        subentry.unique_id
        == {
            "device": f"bn_{source_device.id}",
            "entity": "bn_motion-battery",
        }[source_form["step_id"]]
    )


@pytest.mark.parametrize(
    ("mock_library", "mock_library_updater"),
    [
        pytest.param(True, False, id="current-library"),
        pytest.param(False, True, id="refresh-library"),
    ],
    indirect=True,
)
async def test_library_loading(
    hass: HomeAssistant,
    source_form: SubentryFlowResult,
    selection_input: dict[str, str],
    mock_library: MagicMock,
    mock_library_updater: MagicMock,
) -> None:
    """Test library refresh and loading before the model lookup."""
    result = await hass.config_entries.subentries.async_configure(
        source_form["flow_id"], selection_input
    )

    assert result["step_id"] == "battery"
    mock_library_updater.time_to_update_library.assert_awaited_once_with(1)
    assert mock_library_updater.get_library_updates.await_count == int(
        mock_library_updater.time_to_update_library.return_value
    )
    assert mock_library.load_libraries.await_count == int(not mock_library.is_loaded)
    mock_library.get_device_battery_details.assert_awaited_once_with(
        ModelInfo("Acme", "Motion sensor", "MS1", "1.0")
    )


async def test_unknown_model(
    hass: HomeAssistant,
    source_form: SubentryFlowResult,
    selection_input: dict[str, str],
    mock_library: MagicMock,
) -> None:
    """Test a model absent from the library can be configured manually."""
    mock_library.get_device_battery_details.return_value = None

    result = await hass.config_entries.subentries.async_configure(
        source_form["flow_id"], selection_input
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"
    defaults = result["data_schema"](
        {CONF_BATTERY_TYPE: "AAA", CONF_ADVANCED_SETTINGS: {}}
    )
    assert defaults[CONF_BATTERY_QUANTITY] == 1

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], defaults
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BATTERY_TYPE] == "AAA"
    assert result["data"][CONF_ADVANCED_SETTINGS] == {
        CONF_BATTERY_PERCENTAGE_TEMPLATE: None,
        CONF_BATTERY_LOW_TEMPLATE: None,
        CONF_RETAIN_STATE: False,
        CONF_FILTER_OUTLIERS: False,
    }
    assert (
        result["title"]
        == {"device": "Hall motion", "entity": "Hall motion - Battery"}[
            source_form["step_id"]
        ]
    )


async def test_device_without_model(
    hass: HomeAssistant,
    source_form: SubentryFlowResult,
    selection_input: dict[str, str],
    source_device: dr.DeviceEntry,
    mock_library: MagicMock,
) -> None:
    """Test a device without model information can be configured without a lookup."""
    dr.async_get(hass).async_update_device(
        source_device.id, manufacturer=None, model=None
    )

    result = await hass.config_entries.subentries.async_configure(
        source_form["flow_id"], selection_input
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"
    assert result["description_placeholders"]["manufacturer"] == ""
    assert result["description_placeholders"]["model"] == ""
    mock_library.get_device_battery_details.assert_not_awaited()

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], deepcopy(BATTERY_INPUT)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DEVICE_ID] == source_device.id


async def test_manual_model(
    hass: HomeAssistant,
    source_form: SubentryFlowResult,
    selection_input: dict[str, str],
    mock_library: MagicMock,
) -> None:
    """Test manual library entries show confirmation before entering battery details."""
    mock_library.get_device_battery_details.return_value = DeviceBatteryDetails(
        "Acme", "Motion sensor", "MS1", "1.0", "Manual", 1
    )

    result = await hass.config_entries.subentries.async_configure(
        source_form["flow_id"], selection_input
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "manual"
    assert result["errors"] == {}

    result = await hass.config_entries.subentries.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], deepcopy(BATTERY_INPUT)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_BATTERY_TYPE] == "CR2032"


async def test_duplicate_subentry(
    hass: HomeAssistant,
    source_form: SubentryFlowResult,
    selection_input: dict[str, str],
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test the same source cannot be added again under a different name."""
    first = await hass.config_entries.subentries.async_configure(
        source_form["flow_id"], selection_input
    )
    first = await hass.config_entries.subentries.async_configure(
        first["flow_id"], deepcopy(BATTERY_INPUT)
    )
    assert first["type"] is FlowResultType.CREATE_ENTRY

    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, SUBENTRY_BATTERY_NOTE),
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": source_form["step_id"]}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**selection_input, CONF_NAME: "Another name"}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], deepcopy(BATTERY_INPUT)
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert len(mock_config_entry.subentries) == 1


async def test_entity_error_recovery(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    source_entity: er.RegistryEntry,
    mock_library: MagicMock,
) -> None:
    """Test an unregistered entity error can be corrected with a standalone entity."""
    entity_registry.async_update_entity(source_entity.entity_id, device_id=None)
    result = await hass.config_entries.subentries.async_init(
        (mock_config_entry.entry_id, SUBENTRY_BATTERY_NOTE),
        context={"source": SOURCE_USER},
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"next_step_id": "entity"}
    )
    assert result["data_schema"].schema[CONF_SOURCE_ENTITY_ID].config == {
        "multiple": False,
        "reorder": False,
    }

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_SOURCE_ENTITY_ID: "sensor.unregistered_battery"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "entity"
    assert result["errors"] == {"base": "unconfigurable_entity"}

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_SOURCE_ENTITY_ID: source_entity.entity_id}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "battery"
    assert result["errors"] == {}
    assert result["description_placeholders"] == {
        "name": "Battery",
        "manufacturer": "",
        "model": "",
        "model_id": "",
        "hw_version": "",
    }

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], deepcopy(BATTERY_INPUT)
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Battery"
    assert result["data"] == {
        **BATTERY_INPUT,
        CONF_SOURCE_ENTITY_ID: source_entity.entity_id,
    }
    mock_library.get_device_battery_details.assert_not_awaited()


async def test_reconfigure_suggested_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_subentry: ConfigSubentry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test reconfiguration suggests saved values without mutating the note."""
    original_data = deepcopy(dict(mock_subentry.data))
    result = await mock_config_entry.start_subentry_reconfigure_flow(
        hass, mock_subentry.subentry_id
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {}
    assert result["description_placeholders"] == {
        "manufacturer": "Acme",
        "model": "Motion sensor",
        "model_id": "MS1",
        "hw_version": "1.0",
    }
    schema = result["data_schema"].schema.copy()
    advanced_schema = schema.pop(CONF_ADVANCED_SETTINGS).schema.schema
    assert {
        **{key.schema: get_schema_suggested_value(schema, key) for key in schema},
        CONF_ADVANCED_SETTINGS: {
            key.schema: get_schema_suggested_value(advanced_schema, key)
            for key in advanced_schema
        },
    } == snapshot
    assert mock_subentry.data == original_data


@pytest.mark.parametrize(
    ("name_input", "expected_title"),
    [
        pytest.param({CONF_NAME: "New battery name"}, "New battery name", id="rename"),
        pytest.param({}, "Hall battery", id="keep-name"),
    ],
)
async def test_reconfigure(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_subentry: ConfigSubentry,
    name_input: dict[str, str],
    expected_title: str,
) -> None:
    """Test reconfiguring battery details keeps the same subentry and source."""
    result = await mock_config_entry.start_subentry_reconfigure_flow(
        hass, mock_subentry.subentry_id
    )
    changes = {
        **deepcopy(BATTERY_INPUT),
        CONF_BATTERY_TYPE: "AAA",
        CONF_BATTERY_QUANTITY: 4.0,
        CONF_BATTERY_LOW_THRESHOLD: 20.0,
        CONF_BATTERY_INCREASE_THRESHOLD: 40.0,
        CONF_NOTE: "New note",
        CONF_ADVANCED_SETTINGS: {
            CONF_BATTERY_PERCENTAGE_TEMPLATE: "{{ 75 }}",
            CONF_BATTERY_LOW_TEMPLATE: "{{ true }}",
            CONF_RETAIN_STATE: False,
            CONF_FILTER_OUTLIERS: False,
        },
    }
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {**deepcopy(changes), **name_input}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    updated = mock_config_entry.subentries[mock_subentry.subentry_id]
    assert updated.title == expected_title
    assert updated.unique_id == mock_subentry.unique_id
    assert updated.data == {**mock_subentry.data, **changes}
    assert CONF_NAME not in updated.data
    assert len(mock_config_entry.subentries) == 1


@pytest.mark.parametrize(
    "advanced_input",
    [
        pytest.param({}, id="omitted"),
        pytest.param(
            {CONF_BATTERY_PERCENTAGE_TEMPLATE: "", CONF_BATTERY_LOW_TEMPLATE: ""},
            id="empty",
        ),
        pytest.param(
            {CONF_BATTERY_PERCENTAGE_TEMPLATE: "  ", CONF_BATTERY_LOW_TEMPLATE: "\n "},
            id="whitespace",
        ),
    ],
)
async def test_reconfigure_clear_templates(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_subentry: ConfigSubentry,
    advanced_input: dict[str, str],
) -> None:
    """Test removing templates clears saved templates and resets advanced flags."""
    result = await mock_config_entry.start_subentry_reconfigure_flow(
        hass, mock_subentry.subentry_id
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {**deepcopy(BATTERY_INPUT), CONF_ADVANCED_SETTINGS: advanced_input},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.subentries[mock_subentry.subentry_id].data[
        CONF_ADVANCED_SETTINGS
    ] == {
        CONF_BATTERY_PERCENTAGE_TEMPLATE: None,
        CONF_BATTERY_LOW_TEMPLATE: None,
        CONF_RETAIN_STATE: False,
        CONF_FILTER_OUTLIERS: False,
    }


@pytest.mark.parametrize(
    "removed_fields",
    [
        pytest.param((CONF_ADVANCED_SETTINGS,), id="device"),
        pytest.param((CONF_ADVANCED_SETTINGS, CONF_DEVICE_ID), id="standalone-entity"),
    ],
)
async def test_reconfigure_without_advanced_settings(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_subentry: ConfigSubentry,
    removed_fields: tuple[str, ...],
) -> None:
    """Test notes without saved advanced settings can still be reconfigured."""
    old_data = dict(mock_subentry.data)
    for field in removed_fields:
        old_data.pop(field)
    hass.config_entries.async_update_subentry(
        mock_config_entry, mock_subentry, data=old_data
    )

    result = await mock_config_entry.start_subentry_reconfigure_flow(
        hass, mock_subentry.subentry_id
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {}
    assert mock_config_entry.subentries[mock_subentry.subentry_id].data == old_data

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], deepcopy(BATTERY_INPUT)
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.subentries[mock_subentry.subentry_id].data == {
        **old_data,
        **BATTERY_INPUT,
    }


async def test_reconfigure_orphaned_device(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_subentry: ConfigSubentry,
    device_registry: dr.DeviceRegistry,
) -> None:
    """Test a missing source device is reported when reconfiguring a note."""
    device_registry.async_remove_device(mock_subentry.data[CONF_DEVICE_ID])

    result = await mock_config_entry.start_subentry_reconfigure_flow(
        hass, mock_subentry.subentry_id
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"
    assert result["errors"] == {"base": "orphaned_battery_note"}


async def test_create_subentry_with_other_note(
    hass: HomeAssistant,
    source_form: SubentryFlowResult,
    selection_input: dict[str, str],
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test a note for a different source does not prevent adding a subentry."""
    hass.config_entries.async_add_subentry(
        mock_config_entry,
        ConfigSubentry(
            data=MappingProxyType({CONF_DEVICE_ID: "other-device"}),
            title="Other battery note",
            subentry_type=SUBENTRY_BATTERY_NOTE,
            unique_id="bn_other-device",
        ),
    )
    result = await hass.config_entries.subentries.async_configure(
        source_form["flow_id"], selection_input
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], deepcopy(BATTERY_INPUT)
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert len(mock_config_entry.subentries) == 2


async def test_reconfigure_device_without_model(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_subentry: ConfigSubentry,
) -> None:
    """Test an existing device without model details can still be reconfigured."""
    dr.async_get(hass).async_update_device(
        mock_subentry.data[CONF_DEVICE_ID], manufacturer=None, model=None
    )
    result = await mock_config_entry.start_subentry_reconfigure_flow(
        hass, mock_subentry.subentry_id
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {}
    assert result["description_placeholders"] == {
        "manufacturer": "",
        "model": "",
        "model_id": "",
        "hw_version": "",
    }
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], deepcopy(BATTERY_INPUT)
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"


def test_entity_title_without_device_details(
    hass: HomeAssistant,
    source_entity: er.RegistryEntry,
) -> None:
    """Test an entity keeps its own name when its device cannot be looked up."""
    with patch.object(dr.async_get(hass), "async_get", return_value=None):
        assert calc_config_attributes(
            hass, {CONF_SOURCE_ENTITY_ID: source_entity.entity_id}
        ) == ("bn_motion-battery", "Battery")

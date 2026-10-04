"""Fixtures for Battery Notes tests."""

from collections.abc import Generator
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
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
    SUBENTRY_BATTERY_NOTE,
)
from custom_components.battery_notes.library import DATA_LIBRARY, Library
from pytest_homeassistant_custom_component.common import MockConfigEntry, load_fixture

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_DEVICE_ID,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)


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
def mock_library_updater() -> Generator[MagicMock]:
    """Mock library downloads, schema copying, and the daily update subscription."""
    with patch(
        "custom_components.battery_notes.LibraryUpdater", autospec=True
    ) as updater:
        yield updater.return_value


@pytest.fixture
def mock_config_entry(request: pytest.FixtureRequest) -> MockConfigEntry:
    """Create a Battery Notes entry with default options."""
    options = {
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
    overrides = getattr(request, "param", {})
    advanced_options = {
        **options[CONF_ADVANCED_SETTINGS],
        **overrides.get(CONF_ADVANCED_SETTINGS, {}),
    }
    options.update(overrides)
    options[CONF_ADVANCED_SETTINGS] = advanced_options
    return MockConfigEntry(
        domain=DOMAIN,
        title="Battery Notes",
        version=4,
        data={},
        options=options,
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


@pytest.fixture(
    params=[
        pytest.param("device", id="device"),
        pytest.param("entity", id="entity"),
        pytest.param("standalone-entity", id="standalone-entity"),
    ]
)
def battery_note_source(request: pytest.FixtureRequest) -> str:
    """Select the source of the saved battery note."""
    return request.param


@pytest.fixture
def battery_note_device(
    hass: HomeAssistant, device_registry: dr.DeviceRegistry
) -> dr.DeviceEntry:
    """Register a device belonging to another integration."""
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    return device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={("test", "door-sensor")},
        name="Door sensor",
        manufacturer="Test Manufacturer",
        model="Door sensor",
    )


@pytest.fixture
def battery_note_sensor(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    battery_note_device: dr.DeviceEntry,
    battery_note_source: str,
) -> er.RegistryEntry:
    """Register a source battery sensor and publish its state."""
    entity = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "door-battery",
        suggested_object_id="door_battery",
        original_name="Battery",
        original_device_class=SensorDeviceClass.BATTERY,
        unit_of_measurement=PERCENTAGE,
        device_id={
            "device": battery_note_device.id,
            "entity": battery_note_device.id,
            "standalone-entity": None,
        }[battery_note_source],
    )
    hass.states.async_set(
        entity.entity_id,
        "55",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
        },
    )
    return entity


@pytest.fixture
def mock_battery_note_subentry(
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_note_source: str,
) -> ConfigSubentry:
    """Create a saved note linked to a device or entity."""
    source_data = {
        "device": {CONF_DEVICE_ID: battery_note_device.id},
        "entity": {
            CONF_DEVICE_ID: battery_note_device.id,
            CONF_SOURCE_ENTITY_ID: battery_note_sensor.entity_id,
        },
        "standalone-entity": {CONF_SOURCE_ENTITY_ID: battery_note_sensor.entity_id},
    }[battery_note_source]
    return ConfigSubentry(
        data=MappingProxyType(
            {
                **source_data,
                CONF_BATTERY_TYPE: "AA",
                CONF_BATTERY_QUANTITY: 2,
                CONF_ADVANCED_SETTINGS: {},
            }
        ),
        subentry_id="battery-note-subentry",
        subentry_type=SUBENTRY_BATTERY_NOTE,
        title="Door battery note",
        unique_id="bn_door_battery",
    )


@pytest.fixture
def battery_note_config_entry(
    mock_config_entry: MockConfigEntry, mock_battery_note_subentry: ConfigSubentry
) -> MockConfigEntry:
    """Add the saved note to the parent entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=mock_config_entry.version,
        title=mock_config_entry.title,
        data=mock_config_entry.data,
        options=mock_config_entry.options,
        subentries_data=[mock_battery_note_subentry.as_dict()],
    )


@pytest.fixture
def battery_note_area(
    request: pytest.FixtureRequest,
    battery_note_sensor: er.RegistryEntry,
    battery_note_device: dr.DeviceEntry,
    hass: HomeAssistant,
) -> str | None:
    """Optionally assign an area to the source device and entity."""
    area_name = getattr(request, "param", None)
    if area_name is not None:
        area = ar.async_get(hass).async_create(area_name)
        dr.async_get(hass).async_update_device(battery_note_device.id, area_id=area.id)
        er.async_get(hass).async_update_entity(
            battery_note_sensor.entity_id, area_id=area.id
        )
    return area_name

"""Tests for loading device and entity battery note subentries."""

from types import MappingProxyType

import pytest
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_NOTE,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    SUBENTRY_BATTERY_NOTE,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_FRIENDLY_NAME,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_DEVICE_ID,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep source creation and battery-report timestamps stable in snapshots."""
    freezer.move_to("2026-01-01T12:00:00+00:00")


@pytest.fixture(
    params=[
        pytest.param("device", id="device"),
        pytest.param("entity", id="entity"),
        pytest.param("standalone-entity", id="standalone-entity"),
    ]
)
def note_source(request: pytest.FixtureRequest) -> str:
    """Select how the saved note identifies its source."""
    return request.param


@pytest.fixture
def source_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Register the integration owning the mock source sensors."""
    entry = MockConfigEntry(domain="test")
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def source_device(
    device_registry: dr.DeviceRegistry, source_config_entry: MockConfigEntry
) -> dr.DeviceEntry:
    """Register a mock battery-powered device."""
    return device_registry.async_get_or_create(
        config_entry_id=source_config_entry.entry_id,
        identifiers={("test", "door-sensor")},
        name="Door sensor",
        manufacturer="Test Manufacturer",
        model="Door sensor",
    )


@pytest.fixture(
    params=[
        pytest.param("sensor", id="percentage"),
        pytest.param("binary_sensor", id="binary"),
    ]
)
def source_sensor(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    source_device: dr.DeviceEntry,
    note_source: str,
    request: pytest.FixtureRequest,
) -> er.RegistryEntry:
    """Register a source battery sensor and publish its initial state."""
    domain = request.param
    unit = {"sensor": PERCENTAGE, "binary_sensor": None}[domain]
    entity = entity_registry.async_get_or_create(
        domain,
        "test",
        "door-battery",
        suggested_object_id="door_battery",
        original_name="Battery",
        original_device_class=SensorDeviceClass.BATTERY,
        unit_of_measurement=unit,
        device_id={
            "device": source_device.id,
            "entity": source_device.id,
            "standalone-entity": None,
        }[note_source],
    )
    attributes = {
        ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
        ATTR_FRIENDLY_NAME: "Door battery",
        **{"sensor": {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}, "binary_sensor": {}}[
            domain
        ],
    }
    hass.states.async_set(
        entity.entity_id, {"sensor": "55", "binary_sensor": "off"}[domain], attributes
    )

    for object_id, device_class, unit in (
        ("a_temperature", SensorDeviceClass.TEMPERATURE, "°C"),
        ("b_battery_voltage", SensorDeviceClass.BATTERY, "V"),
    ):
        other_entity = entity_registry.async_get_or_create(
            "sensor",
            "test",
            object_id,
            suggested_object_id=object_id,
            device_id=source_device.id,
            original_device_class=device_class,
            unit_of_measurement=unit,
        )
        hass.states.async_set(
            other_entity.entity_id,
            "3",
            {ATTR_DEVICE_CLASS: device_class, ATTR_UNIT_OF_MEASUREMENT: unit},
        )
    return entity


@pytest.fixture
def mock_subentry(
    source_device: dr.DeviceEntry,
    source_sensor: er.RegistryEntry,
    note_source: str,
) -> ConfigSubentry:
    """Create a saved note pointing to a mock device or battery entity."""
    source_data = {
        "device": {CONF_DEVICE_ID: source_device.id},
        "entity": {
            CONF_DEVICE_ID: source_device.id,
            CONF_SOURCE_ENTITY_ID: source_sensor.entity_id,
        },
        "standalone-entity": {CONF_SOURCE_ENTITY_ID: source_sensor.entity_id},
    }[note_source]
    return ConfigSubentry(
        data=MappingProxyType(
            {
                **source_data,
                CONF_BATTERY_TYPE: "AA",
                CONF_BATTERY_QUANTITY: 2,
                CONF_BATTERY_LOW_THRESHOLD: 15,
                CONF_BATTERY_INCREASE_THRESHOLD: 25,
                CONF_NOTE: "Under the cover",
                CONF_ADVANCED_SETTINGS: {},
            }
        ),
        subentry_id="battery-note-subentry",
        subentry_type=SUBENTRY_BATTERY_NOTE,
        title="Door battery note",
        unique_id="bn_door_battery",
    )


@pytest.fixture
def mock_config_entry(
    mock_config_entry: MockConfigEntry, mock_subentry: ConfigSubentry
) -> MockConfigEntry:
    """Add the saved note to the parent entry before integration setup."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=mock_config_entry.version,
        title=mock_config_entry.title,
        data=mock_config_entry.data,
        options=mock_config_entry.options,
        subentries_data=[mock_subentry.as_dict()],
    )


async def test_setup_subentry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    source_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test note setup creates the expected entities and attaches them to the source."""
    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    mock_subentry = next(iter(mock_config_entry.subentries.values()))
    assert (
        mock_config_entry.runtime_data.loaded_subentries == mock_config_entry.subentries
    )
    coordinator = mock_config_entry.runtime_data.subentry_coordinators[
        mock_subentry.subentry_id
    ]
    assert not coordinator.is_orphaned
    wrapped_source = {
        "sensor": coordinator.wrapped_battery,
        "binary_sensor": coordinator.wrapped_battery_low,
    }[source_sensor.domain]
    assert wrapped_source is not None
    assert wrapped_source.entity_id == source_sensor.entity_id
    assert (
        mock_config_entry.runtime_data.loaded_subentries[mock_subentry.subentry_id]
        == mock_subentry
    )

    entries = er.async_entries_for_config_entry(
        entity_registry, mock_config_entry.entry_id
    )
    assert entries
    expected_device_id = mock_subentry.data.get(CONF_DEVICE_ID)
    for entry in entries:
        assert entry.config_subentry_id == mock_subentry.subentry_id
        assert entry.device_id == expected_device_id
        assert hass.states.get(entry.entity_id) is not None

    assert {
        entry.entity_id: {
            "registry_entry": entry,
            "state": hass.states.get(entry.entity_id),
        }
        for entry in entries
    } == snapshot(exclude=props("device_id"))


async def test_subentry_follows_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_subentry: ConfigSubentry,
    source_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test loaded notes respond to real source battery state changes."""
    await setup_integration(hass, mock_config_entry)
    assert mock_config_entry.state is ConfigEntryState.LOADED

    source_state = hass.states.get(source_sensor.entity_id)
    assert source_state is not None
    hass.states.async_set(
        source_sensor.entity_id,
        {"sensor": "5", "binary_sensor": "on"}[source_sensor.domain],
        source_state.attributes,
    )
    await hass.async_block_till_done()

    suffix = {"sensor": "_battery_plus", "binary_sensor": "_battery_low"}[
        source_sensor.domain
    ]
    target_entity_id = entity_registry.async_get_entity_id(
        source_sensor.domain, DOMAIN, f"{mock_subentry.unique_id}{suffix}"
    )
    assert target_entity_id is not None
    state = hass.states.get(target_entity_id)
    assert state is not None
    assert state.state == {"sensor": "5.0", "binary_sensor": "on"}[source_sensor.domain]

    low_entity_id = entity_registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"{mock_subentry.unique_id}_battery_low"
    )
    assert low_entity_id is not None
    low_state = hass.states.get(low_entity_id)
    assert low_state is not None
    assert low_state.state == "on"

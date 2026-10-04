"""Tests for loading device and entity battery note subentries."""

from datetime import timedelta
from types import MappingProxyType
from unittest.mock import patch

import pytest
from custom_components.battery_notes.common import missing_device_issue_id
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
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
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
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)
from homeassistant.util import dt as dt_util

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


@pytest.fixture
async def orphaned_config_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    note_source: str,
    source_sensor: er.RegistryEntry,
) -> MockConfigEntry:
    """Load a saved note after its source has been removed from the registry."""
    subentry = next(iter(mock_config_entry.subentries.values()))
    remove_source, source_id = {
        "device": (
            dr.async_get(hass).async_remove_device,
            subentry.data.get(CONF_DEVICE_ID),
        ),
        "entity": (er.async_get(hass).async_remove, source_sensor.entity_id),
        "standalone-entity": (er.async_get(hass).async_remove, source_sensor.entity_id),
    }[note_source]
    remove_source(source_id)
    await hass.async_block_till_done()
    await setup_integration(hass, mock_config_entry)

    assert mock_config_entry.state is ConfigEntryState.LOADED
    assert mock_config_entry.runtime_data.subentry_coordinators[
        subentry.subentry_id
    ].is_orphaned
    assert not er.async_entries_for_config_entry(
        er.async_get(hass), mock_config_entry.entry_id
    )
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, missing_device_issue_id(subentry.subentry_id)
        )
        is None
    )
    return mock_config_entry


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


async def test_link_retry_restores_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    note_source: str,
    source_sensor: er.RegistryEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a source available at the retry causes a reload and creates entities."""
    entry = mock_config_entry
    subentry = next(iter(entry.subentries.values()))
    source_registry = {
        "device": dr.async_get(hass),
        "entity": er.async_get(hass),
        "standalone-entity": er.async_get(hass),
    }[note_source]
    with patch.object(source_registry, "async_get", return_value=None):
        await setup_integration(hass, entry)

    coordinator = entry.runtime_data.subentry_coordinators[subentry.subentry_id]
    assert coordinator.is_orphaned
    assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    issue_id = missing_device_issue_id(subentry.subentry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload_entry:
        freezer.tick(timedelta(seconds=119))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)

        reload_entry.assert_not_awaited()
        assert coordinator.is_orphaned
        assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)

        reload_entry.assert_awaited_once_with(entry.entry_id)
        assert not coordinator.is_orphaned
        assert entry.state is ConfigEntryState.LOADED
        restored_coordinator = entry.runtime_data.subentry_coordinators[
            subentry.subentry_id
        ]
        assert restored_coordinator is not coordinator
        assert not restored_coordinator.is_orphaned
        wrapped_source = {
            "sensor": restored_coordinator.wrapped_battery,
            "binary_sensor": restored_coordinator.wrapped_battery_low,
        }[source_sensor.domain]
        assert wrapped_source is not None
        assert wrapped_source.entity_id == source_sensor.entity_id
        entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        assert entities
        assert all(
            entity.config_subentry_id == subentry.subentry_id for entity in entities
        )
        suffix = {"sensor": "_battery_plus", "binary_sensor": "_battery_low"}[
            source_sensor.domain
        ]
        entity_id = er.async_get(hass).async_get_entity_id(
            source_sensor.domain, DOMAIN, f"{subentry.unique_id}{suffix}"
        )
        assert entity_id is not None
        state = hass.states.get(entity_id)
        assert state is not None
        assert (
            state.state
            == {"sensor": "55.0", "binary_sensor": "off"}[source_sensor.domain]
        )
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

        freezer.tick(timedelta(minutes=2))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)
        reload_entry.assert_awaited_once_with(entry.entry_id)


async def test_link_retry_source_still_missing(
    hass: HomeAssistant,
    orphaned_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test a source missing after two minutes creates one repair without reloading."""
    entry = orphaned_config_entry
    subentry = next(iter(entry.subentries.values()))
    coordinator = entry.runtime_data.subentry_coordinators[subentry.subentry_id]
    issue_id = missing_device_issue_id(subentry.subentry_id)
    with (
        patch.object(hass.config_entries, "async_reload") as reload_entry,
        patch(
            "custom_components.battery_notes.coordinator.ir.async_create_issue",
            wraps=ir.async_create_issue,
        ) as create_issue,
    ):
        freezer.tick(timedelta(seconds=119))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)
        create_issue.assert_not_called()
        reload_entry.assert_not_awaited()

        freezer.tick(timedelta(seconds=1))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)

        issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
        assert issue is not None
        assert issue.is_fixable
        assert issue.severity is ir.IssueSeverity.WARNING
        assert issue.translation_key == "missing_device"
        assert issue.translation_placeholders == {"name": subentry.title}
        assert issue.data == {
            "entry_id": entry.entry_id,
            "subentry_id": subentry.subentry_id,
            "device_id": coordinator.device_id,
            "source_entity_id": coordinator.source_entity_id,
        }
        assert coordinator.is_orphaned
        assert not er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        create_issue.assert_called_once()
        reload_entry.assert_not_awaited()

        freezer.tick(timedelta(minutes=2))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)
        create_issue.assert_called_once()
        reload_entry.assert_not_awaited()


@pytest.mark.parametrize(
    "operation",
    [
        pytest.param("async_unload", id="unload"),
        pytest.param("async_remove", id="remove"),
    ],
)
async def test_link_retry_cancelled_on_unload(
    hass: HomeAssistant,
    orphaned_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    operation: str,
) -> None:
    """Test unloading or removing the entry cancels the pending source retry."""
    entry = orphaned_config_entry
    subentry = next(iter(entry.subentries.values()))
    assert await getattr(hass.config_entries, operation)(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED

    with (
        patch.object(hass.config_entries, "async_reload") as reload_entry,
        patch(
            "custom_components.battery_notes.coordinator.ir.async_create_issue",
            wraps=ir.async_create_issue,
        ) as create_issue,
    ):
        freezer.tick(timedelta(minutes=2))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)

    reload_entry.assert_not_awaited()
    create_issue.assert_not_called()
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, missing_device_issue_id(subentry.subentry_id)
        )
        is None
    )

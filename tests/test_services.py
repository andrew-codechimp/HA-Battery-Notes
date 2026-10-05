"""Tests for Battery Notes services."""

from datetime import datetime, timedelta
from types import MappingProxyType

import pytest
from custom_components.battery_notes.const import (
    ATTR_AREA_NAME,
    ATTR_BATTERY_LAST_REPLACED,
    ATTR_BATTERY_LAST_REPLACED_DAYS,
    ATTR_BATTERY_LAST_REPORTED,
    ATTR_BATTERY_LAST_REPORTED_DAYS,
    ATTR_BATTERY_LAST_REPORTED_LEVEL,
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_SOURCE_ENTITY_ID,
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_NOT_REPLACED,
    EVENT_BATTERY_NOT_REPORTED,
    EVENT_BATTERY_REPLACED,
    EVENT_BATTERY_THRESHOLD,
    LAST_REPLACED,
    SERVICE_BATTERY_REPLACED,
    SERVICE_CHECK_BATTERY_LAST_REPLACED,
    SERVICE_CHECK_BATTERY_LAST_REPORTED,
    SERVICE_CHECK_BATTERY_LOW,
    SERVICE_DATA_DATE_TIME_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPORTED,
    SERVICE_DATA_RAISE_EVENTS,
    SUBENTRY_BATTERY_NOTE,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_DEVICE_ID,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep source creation and the default replacement time stable."""
    freezer.move_to("2026-01-01T12:00:00+00:00")


@pytest.mark.parametrize(
    ("date_data", "expected_replaced"),
    [
        pytest.param({}, "2026-01-01T12:00:00+00:00", id="now"),
        pytest.param(
            {SERVICE_DATA_DATE_TIME_REPLACED: "2025-12-20T14:30:00+00:00"},
            "2025-12-20T14:30:00.000001+00:00",
            id="explicit-utc-date",
        ),
        pytest.param(
            {SERVICE_DATA_DATE_TIME_REPLACED: "2025-12-20T14:30:00.123456+02:00"},
            "2025-12-20T12:30:00.000001+00:00",
            id="explicit-offset-date",
        ),
    ],
)
@pytest.mark.parametrize(
    "battery_note_area",
    [pytest.param(None, id="no-area"), pytest.param("Hall", id="with-area")],
    indirect=True,
)
async def test_set_battery_replaced(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_area: str | None,
    date_data: dict[str, str],
    expected_replaced: str,
) -> None:
    """Test setting the replacement date updates storage, sensors, and the event."""
    await setup_integration(hass, battery_note_config_entry)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    entity_registry = er.async_get(hass)
    battery_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{subentry.unique_id}_battery_plus"
    )
    assert battery_id is not None
    battery_before = hass.states.get(battery_id)
    assert battery_before is not None
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)
    source_key = (
        subentry.data.get(CONF_SOURCE_ENTITY_ID) or subentry.data[CONF_DEVICE_ID]
    )
    target_data = {
        field: subentry.data[field]
        for field in (ATTR_DEVICE_ID, ATTR_SOURCE_ENTITY_ID)
        if field in subentry.data
    }

    await hass.services.async_call(
        DOMAIN,
        SERVICE_BATTERY_REPLACED,
        {**target_data, **date_data},
        blocking=True,
    )
    await hass.async_block_till_done()

    replaced_at = datetime.fromisoformat(expected_replaced)
    coordinator = battery_note_config_entry.runtime_data.subentry_coordinators[
        subentry.subentry_id
    ]
    assert coordinator.last_replaced == replaced_at
    store = battery_note_config_entry.runtime_data.store
    stored_entries = {**store.async_get_devices(), **store.async_get_entities()}
    assert stored_entries[source_key][LAST_REPLACED] == replaced_at
    battery_after = hass.states.get(battery_id)
    assert battery_after is not None
    assert battery_after.state == battery_before.state
    assert battery_after.attributes[ATTR_BATTERY_LAST_REPLACED] == replaced_at
    last_replaced_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, f"{subentry.unique_id}_battery_last_replaced"
    )
    assert last_replaced_id is not None
    last_replaced = hass.states.get(last_replaced_id)
    assert last_replaced is not None
    assert last_replaced.state == replaced_at.isoformat(timespec="seconds")
    assert len(events) == 1
    assert events[0].data == {
        ATTR_DEVICE_ID: subentry.data.get(CONF_DEVICE_ID, ""),
        ATTR_SOURCE_ENTITY_ID: subentry.data.get(CONF_SOURCE_ENTITY_ID, ""),
        ATTR_AREA_NAME: battery_note_area,
        ATTR_DEVICE_NAME: "Door battery note",
        ATTR_BATTERY_TYPE_AND_QUANTITY: "2× AA",
        ATTR_BATTERY_TYPE: "AA",
        ATTR_BATTERY_QUANTITY: 2,
    }


@pytest.fixture(
    params=[
        pytest.param("missing-device", id="missing-device"),
        pytest.param("missing-entity", id="missing-entity"),
        pytest.param("unconfigured-device", id="unconfigured-device"),
        pytest.param("unconfigured-entity", id="unconfigured-entity"),
    ]
)
def unconfigured_target(
    request: pytest.FixtureRequest,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
) -> dict[str, str]:
    """Provide missing registry entries and registered sources without notes."""
    return {
        "missing-device": {ATTR_DEVICE_ID: "missing-device"},
        "missing-entity": {ATTR_SOURCE_ENTITY_ID: "sensor.missing_battery"},
        "unconfigured-device": {ATTR_DEVICE_ID: battery_note_device.id},
        "unconfigured-entity": {ATTR_SOURCE_ENTITY_ID: battery_note_sensor.entity_id},
    }[request.param]


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_set_battery_replaced_unconfigured_source(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    unconfigured_target: dict[str, str],
) -> None:
    """Test missing or unconfigured sources raise an error without changing storage."""
    await setup_integration(hass, mock_config_entry)
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)

    with pytest.raises(HomeAssistantError) as error:
        await hass.services.async_call(
            DOMAIN, SERVICE_BATTERY_REPLACED, unconfigured_target, blocking=True
        )
    await hass.async_block_till_done()

    assert error.value.translation_domain == DOMAIN
    assert error.value.translation_key == "not_configured_in_battery_notes"
    assert error.value.translation_placeholders == {
        "source": next(iter(unconfigured_target.values()))
    }
    assert not events
    assert mock_config_entry.runtime_data.store.async_get_devices() == {}
    assert mock_config_entry.runtime_data.store.async_get_entities() == {}


@pytest.mark.parametrize("battery_note_source", ["entity"])
async def test_set_battery_replaced_prefers_device_note(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
) -> None:
    """Test replacing by device updates the device note, not an entity note on it."""
    note_data = {
        CONF_BATTERY_TYPE: "AA",
        CONF_BATTERY_QUANTITY: 2,
        CONF_ADVANCED_SETTINGS: {},
    }
    entity_note = ConfigSubentry(
        data=MappingProxyType(
            {
                **note_data,
                CONF_DEVICE_ID: battery_note_device.id,
                CONF_SOURCE_ENTITY_ID: battery_note_sensor.entity_id,
            }
        ),
        subentry_id="entity-note",
        subentry_type=SUBENTRY_BATTERY_NOTE,
        title="Door entity note",
        unique_id="bn_door_entity",
    )
    device_note = ConfigSubentry(
        data=MappingProxyType({**note_data, CONF_DEVICE_ID: battery_note_device.id}),
        subentry_id="device-note",
        subentry_type=SUBENTRY_BATTERY_NOTE,
        title="Door device note",
        unique_id="bn_door_device",
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=mock_config_entry.version,
        title=mock_config_entry.title,
        data=mock_config_entry.data,
        options=mock_config_entry.options,
        subentries_data=[entity_note.as_dict(), device_note.as_dict()],
    )
    await setup_integration(hass, entry)
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_BATTERY_REPLACED,
        {
            ATTR_DEVICE_ID: battery_note_device.id,
            SERVICE_DATA_DATE_TIME_REPLACED: "2025-12-20T14:30:00+00:00",
        },
        blocking=True,
    )

    replaced_at = datetime.fromisoformat("2025-12-20T14:30:00.000001+00:00")
    coordinators = entry.runtime_data.subentry_coordinators
    assert coordinators["device-note"].last_replaced == replaced_at
    assert coordinators["entity-note"].last_replaced != replaced_at
    assert len(events) == 1
    assert events[0].data[ATTR_DEVICE_NAME] == "Door device note"
    assert events[0].data[ATTR_SOURCE_ENTITY_ID] == ""


@pytest.mark.parametrize(
    ("level", "raise_events"),
    [
        pytest.param("5", True, id="low"),
        pytest.param("5", False, id="low-without-events"),
        pytest.param("55", True, id="not-low"),
    ],
)
async def test_check_battery_low(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    level: str,
    raise_events: bool,
) -> None:
    """Test checking for low batteries raises reminder events and returns them."""
    await setup_integration(hass, battery_note_config_entry)
    hass.states.async_set(
        battery_note_sensor.entity_id,
        level,
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
        },
    )
    await hass.async_block_till_done()
    events = async_capture_events(hass, EVENT_BATTERY_THRESHOLD)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LOW,
        {SERVICE_DATA_RAISE_EVENTS: raise_events},
        blocking=True,
        return_response=True,
    )

    assert response is not None
    items = response["check_battery_battery_low"]
    is_low = level == "5"
    assert len(items) == (1 if is_low else 0)
    for item in items:
        assert item[ATTR_DEVICE_NAME] == "Door battery note"
        assert item[ATTR_BATTERY_LOW] is True
        assert item[ATTR_BATTERY_LEVEL] == 5
        assert item[ATTR_BATTERY_THRESHOLD_REMINDER] is True
    assert len(events) == (1 if is_low and raise_events else 0)
    for event in events:
        assert event.data[ATTR_BATTERY_LOW] is True
        assert event.data[ATTR_BATTERY_THRESHOLD_REMINDER] is True


@pytest.mark.parametrize(
    ("days_last_replaced", "expected_items"),
    [
        pytest.param(30, 1, id="overdue"),
        pytest.param(60, 0, id="recent"),
    ],
)
async def test_check_battery_last_replaced(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    days_last_replaced: int,
    expected_items: int,
) -> None:
    """Test batteries replaced longer ago than the given days are reported."""
    await setup_integration(hass, battery_note_config_entry)
    freezer.tick(timedelta(days=40))
    events = async_capture_events(hass, EVENT_BATTERY_NOT_REPLACED)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LAST_REPLACED,
        {SERVICE_DATA_DAYS_LAST_REPLACED: days_last_replaced},
        blocking=True,
        return_response=True,
    )

    assert response is not None
    items = response["check_battery_last_replaced"]
    assert len(items) == expected_items
    assert len(events) == expected_items
    for data in (*items, *(event.data for event in events)):
        assert data[ATTR_DEVICE_NAME] == "Door battery note"
        assert data[ATTR_BATTERY_LAST_REPLACED_DAYS] == 40
    for item in items:
        assert item[ATTR_BATTERY_LAST_REPLACED] == "2026-01-01T12:00:00+00:00"


@pytest.mark.parametrize(
    ("days_last_reported", "expected_items"),
    [
        pytest.param(2, 1, id="not-reported"),
        pytest.param(5, 0, id="recently-reported"),
    ],
)
async def test_check_battery_last_reported(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    days_last_reported: int,
    expected_items: int,
) -> None:
    """Test batteries not reported for longer than the given days are reported."""
    await setup_integration(hass, battery_note_config_entry)
    freezer.tick(timedelta(days=3))
    events = async_capture_events(hass, EVENT_BATTERY_NOT_REPORTED)

    response = await hass.services.async_call(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LAST_REPORTED,
        {SERVICE_DATA_DAYS_LAST_REPORTED: days_last_reported},
        blocking=True,
        return_response=True,
    )

    assert response is not None
    items = response["check_battery_last_reported"]
    assert len(items) == expected_items
    assert len(events) == expected_items
    for data in (*items, *(event.data for event in events)):
        assert data[ATTR_DEVICE_NAME] == "Door battery note"
        assert data[ATTR_BATTERY_LAST_REPORTED_DAYS] == 3
        assert data[ATTR_BATTERY_LAST_REPORTED_LEVEL] == 55
    for item in items:
        assert item[ATTR_BATTERY_LAST_REPORTED] == "2026-01-01T12:00:00+00:00"


@pytest.mark.parametrize(
    "entity_area",
    [
        pytest.param(None, id="inherits-device-area"),
        pytest.param("Garage", id="entity-area-override"),
    ],
)
@pytest.mark.parametrize("battery_note_source", ["device", "entity"])
async def test_battery_replaced_area(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    entity_area: str | None,
) -> None:
    """Test events use the source entity's own area or else its device's area."""
    area_registry = ar.async_get(hass)
    dr.async_get(hass).async_update_device(
        battery_note_device.id, area_id=area_registry.async_create("Hall").id
    )
    if entity_area:
        er.async_get(hass).async_update_entity(
            battery_note_sensor.entity_id,
            area_id=area_registry.async_create(entity_area).id,
        )
    await setup_integration(hass, battery_note_config_entry)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_BATTERY_REPLACED,
        {ATTR_DEVICE_ID: subentry.data[CONF_DEVICE_ID]}
        if CONF_SOURCE_ENTITY_ID not in subentry.data
        else {ATTR_SOURCE_ENTITY_ID: subentry.data[CONF_SOURCE_ENTITY_ID]},
        blocking=True,
    )

    assert len(events) == 1
    # Entity area overrides only apply to entity notes
    is_entity_note = CONF_SOURCE_ENTITY_ID in subentry.data
    assert events[0].data[ATTR_AREA_NAME] == (
        (entity_area or "Hall") if is_entity_note else "Hall"
    )

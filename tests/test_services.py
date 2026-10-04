"""Tests for Battery Notes services."""

from datetime import datetime

import pytest
from custom_components.battery_notes.const import (
    ATTR_AREA_NAME,
    ATTR_BATTERY_LAST_REPLACED,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_SOURCE_ENTITY_ID,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_REPLACED,
    LAST_REPLACED,
    SERVICE_BATTERY_REPLACED,
    SERVICE_DATA_DATE_TIME_REPLACED,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er

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

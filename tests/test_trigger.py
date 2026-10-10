"""Tests for Battery Notes replacement triggers."""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import voluptuous as vol
from custom_components.battery_notes.const import (
    ATTR_DEVICE_ID,
    ATTR_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_REPLACED,
    SERVICE_BATTERY_REPLACED,
    SERVICE_DATA_DATE_TIME_REPLACED,
)
from custom_components.battery_notes.trigger import BatteryReplacedTrigger
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from homeassistant.core import CALLBACK_TYPE, Context, HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    label_registry as lr,
)
from homeassistant.helpers.trigger import (
    TriggerConfig,
    async_get_all_descriptions,
    async_initialize_triggers,
    async_validate_trigger_config,
)

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

TRIGGER_KEY = "battery_notes.battery_replaced"
BUTTON_UNIQUE_ID = "bn_door_battery_battery_replaced_button"


async def _attach_trigger(
    hass: HomeAssistant, config: dict[str, Any]
) -> tuple[AsyncMock, CALLBACK_TYPE]:
    """Attach a trigger through Home Assistant's public trigger helpers."""
    config = await async_validate_trigger_config(
        hass, [{"platform": TRIGGER_KEY, "id": "replaced", **config}]
    )
    action = AsyncMock()
    remove = await async_initialize_triggers(
        hass, config, action, "automation", "Battery replaced", Mock()
    )
    assert remove is not None
    return action, remove


@pytest.fixture
async def replacement_targets(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
) -> dict[str, dict[str, str | list[str]]]:
    """Set up a note with standard target memberships."""
    await setup_integration(hass, battery_note_config_entry)
    registry = er.async_get(hass)
    button_id = registry.async_get_entity_id("button", DOMAIN, BUTTON_UNIQUE_ID)
    assert button_id is not None
    type_id = registry.async_get_entity_id(
        "sensor", DOMAIN, "bn_door_battery_battery_type"
    )
    assert type_id is not None
    floor = fr.async_get(hass).async_create("Ground floor")
    area = ar.async_get(hass).async_create("Hall", floor_id=floor.floor_id)
    entity_label = lr.async_get(hass).async_create("Replacement buttons")
    device_label = lr.async_get(hass).async_create("Battery devices")
    area_label = lr.async_get(hass).async_create("Battery areas")
    registry.async_update_entity(button_id, labels={entity_label.label_id})
    registry.async_update_entity(battery_note_sensor.entity_id, area_id=area.id)
    dr.async_get(hass).async_update_device(
        battery_note_device.id, area_id=area.id, labels={device_label.label_id}
    )
    ar.async_get(hass).async_update(area.id, labels={area_label.label_id})
    return {
        "source-entity": {"entity_id": battery_note_sensor.entity_id},
        "note-entity": {"entity_id": type_id},
        "diagnostic-entity": {"entity_id": button_id},
        "device": {"device_id": battery_note_device.id},
        "area": {"area_id": area.id},
        "floor": {"floor_id": floor.floor_id},
        "entity-label": {"label_id": entity_label.label_id},
        "device-label": {"label_id": device_label.label_id},
        "area-label": {"label_id": area_label.label_id},
        "combined": {
            "entity_id": [type_id, button_id, battery_note_sensor.entity_id],
            "device_id": [battery_note_device.id],
            "area_id": [area.id],
            "floor_id": [floor.floor_id],
            "label_id": [entity_label.label_id, device_label.label_id],
        },
        "empty": {},
        "none": {"device_id": "none"},
        "missing-entity": {"entity_id": "sensor.missing"},
        "missing-device": {"device_id": "missing"},
        "missing-area": {"area_id": "missing"},
        "missing-floor": {"floor_id": "missing"},
        "missing-label": {"label_id": "missing"},
    }


@pytest.mark.parametrize(
    ("target_kind", "expected_by_source"),
    [
        pytest.param(kind, {"device": 1, "entity": 1, "standalone-entity": 1}, id=kind)
        for kind in (
            "source-entity",
            "note-entity",
            "diagnostic-entity",
            "area",
            "floor",
            "entity-label",
            "area-label",
            "combined",
        )
    ]
    + [
        pytest.param(kind, {"device": 1, "entity": 1, "standalone-entity": 0}, id=kind)
        for kind in ("device", "device-label")
    ]
    + [
        pytest.param(kind, {"device": 0, "entity": 0, "standalone-entity": 0}, id=kind)
        for kind in (
            "empty",
            "none",
            "missing-entity",
            "missing-device",
            "missing-area",
            "missing-floor",
            "missing-label",
        )
    ],
)
async def test_replacement_targets(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_source: str,
    replacement_targets: dict[str, dict[str, str | list[str]]],
    target_kind: str,
    expected_by_source: dict[str, int],
) -> None:
    """Test replacement actions match standard targets without duplicate runs."""
    action, remove = await _attach_trigger(
        hass, {"target": replacement_targets[target_kind]}
    )
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    service_data = {
        key: subentry.data[key]
        for key in (ATTR_DEVICE_ID, ATTR_SOURCE_ENTITY_ID)
        if key in subentry.data
    }

    await hass.services.async_call(
        DOMAIN,
        SERVICE_BATTERY_REPLACED,
        {**service_data, SERVICE_DATA_DATE_TIME_REPLACED: "2025-01-01T12:00:00+00:00"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert len(events) == 1
    assert action.call_count == expected_by_source[battery_note_source]
    remove()


async def test_omitted_target(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    replacement_targets: dict[str, dict[str, str | list[str]]],
) -> None:
    """Test an omitted target receives action and button events for every source."""
    action, remove = await _attach_trigger(hass, {})
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    service_data = {
        key: subentry.data[key]
        for key in (ATTR_DEVICE_ID, ATTR_SOURCE_ENTITY_ID)
        if key in subentry.data
    }

    await hass.services.async_call(
        DOMAIN, SERVICE_BATTERY_REPLACED, service_data, blocking=True
    )
    await hass.services.async_call(
        "button", "press", replacement_targets["diagnostic-entity"], blocking=True
    )
    await hass.async_block_till_done()

    assert len(events) == 2
    assert action.await_count == 2
    for call, event in zip(action.call_args_list, events, strict=True):
        assert call.args[0]["trigger"] == {
            "id": "replaced",
            "idx": "0",
            "alias": None,
            "platform": TRIGGER_KEY,
            "description": "battery replaced",
            **event.data,
        }
        assert call.args[1] is event.context
    remove()


async def test_replacement_button_payload_and_cleanup(
    hass: HomeAssistant,
    replacement_targets: dict[str, dict[str, str | list[str]]],
) -> None:
    """Test the button trigger exposes all event fields directly on the trigger."""
    action, remove = await _attach_trigger(
        hass, {"target": replacement_targets["diagnostic-entity"]}
    )
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)

    await hass.services.async_call(
        "button", "press", replacement_targets["diagnostic-entity"], blocking=True
    )
    await hass.async_block_till_done()

    assert len(events) == 1
    action.assert_awaited_once()
    trigger = action.call_args.args[0]["trigger"]
    assert trigger == {
        "id": "replaced",
        "idx": "0",
        "alias": None,
        "platform": TRIGGER_KEY,
        "description": "battery replaced",
        **events[0].data,
    }
    assert action.call_args.args[1] is events[0].context
    remove()

    await hass.services.async_call(
        "button", "press", replacement_targets["diagnostic-entity"], blocking=True
    )
    await hass.async_block_till_done()

    assert len(events) == 2
    action.assert_awaited_once()


async def test_event_timing_and_repeated_events(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    replacement_targets: dict[str, dict[str, str | list[str]]],
) -> None:
    """Test each event triggers immediately, independently of state changes."""
    trigger = BatteryReplacedTrigger(
        hass, TriggerConfig(key=TRIGGER_KEY, target=replacement_targets["note-entity"])
    )
    runner = Mock()
    remove = await trigger.async_attach_runner(runner, None)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    data = battery_note_config_entry.runtime_data.subentry_coordinators[
        subentry.subentry_id
    ].event_data()
    context = Context()

    hass.bus.async_fire(EVENT_BATTERY_REPLACED, data, context=context)
    await hass.async_block_till_done()

    runner.assert_called_once_with(data, "battery replaced", context)

    hass.bus.async_fire(EVENT_BATTERY_REPLACED, data, context=context)
    await hass.async_block_till_done()

    assert runner.call_count == 2
    remove()


@pytest.mark.parametrize(
    "target_kind",
    [pytest.param("area", id="area"), pytest.param("entity-label", id="label")],
)
async def test_target_membership_changes(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    replacement_targets: dict[str, dict[str, str | list[str]]],
    target_kind: str,
) -> None:
    """Test targets resolve current registry membership for every event."""
    action, remove = await _attach_trigger(
        hass, {"target": replacement_targets[target_kind]}
    )
    coordinator = next(
        iter(battery_note_config_entry.runtime_data.subentry_coordinators.values())
    )
    data = coordinator.event_data()
    hass.bus.async_fire(EVENT_BATTERY_REPLACED, data)
    await hass.async_block_till_done()
    action.assert_awaited_once()

    registry = er.async_get(hass)
    button_id = registry.async_get_entity_id("button", DOMAIN, BUTTON_UNIQUE_ID)
    assert button_id is not None
    registry.async_update_entity(button_id, labels=set())
    registry.async_update_entity(battery_note_sensor.entity_id, area_id=None)
    dr.async_get(hass).async_update_device(battery_note_device.id, area_id=None)
    await hass.async_block_till_done()
    hass.bus.async_fire(EVENT_BATTERY_REPLACED, data)
    await hass.async_block_till_done()

    action.assert_awaited_once()
    remove()


@pytest.mark.parametrize("battery_note_source", [pytest.param("entity", id="entity")])
async def test_entity_note_does_not_match_other_note_on_device(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    replacement_targets: dict[str, dict[str, str | list[str]]],
) -> None:
    """Test targeting an entity note does not also match its device's note."""
    action, remove = await _attach_trigger(
        hass, {"target": replacement_targets["note-entity"]}
    )
    coordinator = next(
        iter(battery_note_config_entry.runtime_data.subentry_coordinators.values())
    )
    hass.bus.async_fire(
        EVENT_BATTERY_REPLACED,
        {**coordinator.event_data(), ATTR_SOURCE_ENTITY_ID: ""},
    )
    await hass.async_block_till_done()

    action.assert_not_called()

    hass.bus.async_fire(EVENT_BATTERY_REPLACED, coordinator.event_data())
    await hass.async_block_till_done()

    action.assert_awaited_once()
    remove()


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({"target": {"entity_id": "invalid"}}, id="invalid-entity"),
        pytest.param({"target": {}, "options": {"for": 10}}, id="unsupported-option"),
    ],
)
async def test_invalid_config(hass: HomeAssistant, config: dict[str, Any]) -> None:
    """Test invalid target and option configurations are rejected."""
    with pytest.raises(vol.Invalid):
        await async_validate_trigger_config(hass, [{"platform": TRIGGER_KEY, **config}])


async def test_trigger_description(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
) -> None:
    """Test Home Assistant loads the trigger's target selector definition."""
    await setup_integration(hass, battery_note_config_entry)

    descriptions = await async_get_all_descriptions(hass)

    assert descriptions[TRIGGER_KEY] == {
        "fields": {},
        "target": {"entity": [{"integration": "battery_notes"}]},
    }

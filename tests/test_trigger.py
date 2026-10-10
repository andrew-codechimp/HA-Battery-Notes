"""Tests for Battery Notes event triggers."""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import voluptuous as vol
from custom_components.battery_notes.const import (
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_DEVICE_ID,
    ATTR_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_REPLACED,
    EVENT_BATTERY_THRESHOLD,
    SERVICE_BATTERY_REPLACED,
    SERVICE_CHECK_BATTERY_LOW,
    SERVICE_DATA_DATE_TIME_REPLACED,
)
from custom_components.battery_notes.trigger import BatteryWasReplacedTrigger
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

TRIGGER_KEY = "battery_notes.battery_was_replaced"
LOW_TRIGGER_KEY = "battery_notes.battery_became_low"
RECOVERY_TRIGGER_KEY = "battery_notes.battery_no_longer_low"
BUTTON_UNIQUE_ID = "bn_door_battery_battery_replaced_button"


async def _attach_trigger(
    hass: HomeAssistant, config: dict[str, Any], trigger_key: str = TRIGGER_KEY
) -> tuple[AsyncMock, CALLBACK_TYPE]:
    """Attach a trigger through Home Assistant's public trigger helpers."""
    config = await async_validate_trigger_config(
        hass, [{"platform": trigger_key, "id": "replaced", **config}]
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
    ("trigger_key", "event_type", "initial_level", "final_level"),
    [
        pytest.param(TRIGGER_KEY, EVENT_BATTERY_REPLACED, "55", "5", id="replacement"),
        pytest.param(LOW_TRIGGER_KEY, EVENT_BATTERY_THRESHOLD, "55", "5", id="low"),
        pytest.param(
            RECOVERY_TRIGGER_KEY, EVENT_BATTERY_THRESHOLD, "5", "10", id="recovery"
        ),
    ],
)
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
async def test_trigger_targets(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_note_source: str,
    replacement_targets: dict[str, dict[str, str | list[str]]],
    target_kind: str,
    expected_by_source: dict[str, int],
    trigger_key: str,
    event_type: str,
    initial_level: str,
    final_level: str,
) -> None:
    """Test events match standard targets without duplicate runs."""
    source_state = hass.states.get(battery_note_sensor.entity_id)
    assert source_state is not None
    hass.states.async_set(
        battery_note_sensor.entity_id, initial_level, source_state.attributes
    )
    await hass.async_block_till_done()
    action, remove = await _attach_trigger(
        hass, {"target": replacement_targets[target_kind]}, trigger_key
    )
    events = async_capture_events(hass, event_type)
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

    source_state = hass.states.get(battery_note_sensor.entity_id)
    assert source_state is not None
    hass.states.async_set(
        battery_note_sensor.entity_id, final_level, source_state.attributes
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
    trigger = BatteryWasReplacedTrigger(
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
@pytest.mark.parametrize(
    ("trigger_key", "event_type", "battery_low"),
    [
        pytest.param(TRIGGER_KEY, EVENT_BATTERY_REPLACED, True, id="replacement"),
        pytest.param(LOW_TRIGGER_KEY, EVENT_BATTERY_THRESHOLD, True, id="low"),
        pytest.param(
            RECOVERY_TRIGGER_KEY, EVENT_BATTERY_THRESHOLD, False, id="recovery"
        ),
    ],
)
async def test_target_membership_changes(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    replacement_targets: dict[str, dict[str, str | list[str]]],
    target_kind: str,
    trigger_key: str,
    event_type: str,
    battery_low: bool,
) -> None:
    """Test targets resolve current registry membership for every event."""
    action, remove = await _attach_trigger(
        hass, {"target": replacement_targets[target_kind]}, trigger_key
    )
    coordinator = next(
        iter(battery_note_config_entry.runtime_data.subentry_coordinators.values())
    )
    data = coordinator.event_data(
        {ATTR_BATTERY_LOW: battery_low, ATTR_BATTERY_THRESHOLD_REMINDER: False}
    )
    hass.bus.async_fire(event_type, data)
    await hass.async_block_till_done()
    action.assert_awaited_once()

    registry = er.async_get(hass)
    button_id = registry.async_get_entity_id("button", DOMAIN, BUTTON_UNIQUE_ID)
    assert button_id is not None
    registry.async_update_entity(button_id, labels=set())
    registry.async_update_entity(battery_note_sensor.entity_id, area_id=None)
    dr.async_get(hass).async_update_device(battery_note_device.id, area_id=None)
    await hass.async_block_till_done()
    hass.bus.async_fire(event_type, data)
    await hass.async_block_till_done()

    action.assert_awaited_once()
    remove()


@pytest.mark.parametrize("battery_note_source", [pytest.param("entity", id="entity")])
@pytest.mark.parametrize(
    ("trigger_key", "event_type", "battery_low"),
    [
        pytest.param(TRIGGER_KEY, EVENT_BATTERY_REPLACED, True, id="replacement"),
        pytest.param(LOW_TRIGGER_KEY, EVENT_BATTERY_THRESHOLD, True, id="low"),
        pytest.param(
            RECOVERY_TRIGGER_KEY, EVENT_BATTERY_THRESHOLD, False, id="recovery"
        ),
    ],
)
async def test_entity_note_does_not_match_other_note_on_device(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    replacement_targets: dict[str, dict[str, str | list[str]]],
    trigger_key: str,
    event_type: str,
    battery_low: bool,
) -> None:
    """Test targeting an entity note does not also match its device's note."""
    action, remove = await _attach_trigger(
        hass, {"target": replacement_targets["note-entity"]}, trigger_key
    )
    coordinator = next(
        iter(battery_note_config_entry.runtime_data.subentry_coordinators.values())
    )
    data = coordinator.event_data(
        {ATTR_BATTERY_LOW: battery_low, ATTR_BATTERY_THRESHOLD_REMINDER: False}
    )
    hass.bus.async_fire(event_type, {**data, ATTR_SOURCE_ENTITY_ID: ""})
    await hass.async_block_till_done()

    action.assert_not_called()

    hass.bus.async_fire(event_type, data)
    await hass.async_block_till_done()

    action.assert_awaited_once()
    remove()


@pytest.mark.parametrize(
    ("options", "transition_count", "expected_event_indices"),
    [
        pytest.param({}, 1, [0, 1], id="default"),
        pytest.param({"reminder": "exclude"}, 1, [0], id="exclude"),
        pytest.param({"reminder": "only"}, 0, [1], id="only"),
        pytest.param({"reminder": "all"}, 1, [0, 1], id="all"),
    ],
)
async def test_low_transitions_reminders_and_cleanup(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    options: dict[str, str],
    transition_count: int,
    expected_event_indices: list[int],
) -> None:
    """Test source transitions and check-action reminders preserve the event data."""
    await setup_integration(hass, battery_note_config_entry)
    action, remove = await _attach_trigger(hass, {"options": options}, LOW_TRIGGER_KEY)
    events = async_capture_events(hass, EVENT_BATTERY_THRESHOLD)
    source_state = hass.states.get(battery_note_sensor.entity_id)
    assert source_state is not None
    attributes = source_state.attributes
    action.assert_not_called()

    hass.states.async_set(battery_note_sensor.entity_id, "5", attributes)
    await hass.async_block_till_done()
    assert action.await_count == transition_count

    hass.states.async_set(battery_note_sensor.entity_id, "4", attributes)
    await hass.async_block_till_done()
    assert action.await_count == transition_count

    await hass.services.async_call(DOMAIN, SERVICE_CHECK_BATTERY_LOW, blocking=True)
    await hass.async_block_till_done()
    assert len(events) == 2
    assert events[0].data[ATTR_BATTERY_THRESHOLD_REMINDER] is False
    assert events[1].data[ATTR_BATTERY_THRESHOLD_REMINDER] is True
    assert action.await_count == len(expected_event_indices)
    expected_events = [events[index] for index in expected_event_indices]
    for call, event in zip(action.call_args_list, expected_events, strict=True):
        assert call.args[0]["trigger"] == {
            "id": "replaced",
            "idx": "0",
            "alias": None,
            "platform": LOW_TRIGGER_KEY,
            "description": "battery low",
            **event.data,
        }
        assert call.args[1] is event.context

    hass.states.async_set(battery_note_sensor.entity_id, "55", attributes)
    await hass.async_block_till_done()
    assert len(events) == 3
    assert events[2].data[ATTR_BATTERY_LOW] is False
    assert action.await_count == len(expected_event_indices)

    remove()
    hass.states.async_set(battery_note_sensor.entity_id, "5", attributes)
    await hass.async_block_till_done()
    await hass.services.async_call(DOMAIN, SERVICE_CHECK_BATTERY_LOW, blocking=True)
    await hass.async_block_till_done()
    assert len(events) == 5
    assert action.await_count == len(expected_event_indices)


async def test_recovery_transitions_payload_and_cleanup(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
) -> None:
    """Test recovery fires at the threshold and forwards the event unchanged."""
    await setup_integration(hass, battery_note_config_entry)
    action, remove = await _attach_trigger(hass, {}, RECOVERY_TRIGGER_KEY)
    events = async_capture_events(hass, EVENT_BATTERY_THRESHOLD)
    source_state = hass.states.get(battery_note_sensor.entity_id)
    assert source_state is not None
    attributes = source_state.attributes
    action.assert_not_called()

    hass.states.async_set(battery_note_sensor.entity_id, "5", attributes)
    await hass.async_block_till_done()
    await hass.services.async_call(DOMAIN, SERVICE_CHECK_BATTERY_LOW, blocking=True)
    await hass.async_block_till_done()
    assert len(events) == 2
    action.assert_not_called()

    hass.states.async_set(battery_note_sensor.entity_id, "10", attributes)
    await hass.async_block_till_done()
    assert len(events) == 3
    assert events[2].data[ATTR_BATTERY_LOW] is False
    action.assert_awaited_once()
    assert action.call_args.args[0]["trigger"] == {
        "id": "replaced",
        "idx": "0",
        "alias": None,
        "platform": RECOVERY_TRIGGER_KEY,
        "description": "battery no longer low",
        **events[2].data,
    }
    assert action.call_args.args[1] is events[2].context

    hass.states.async_set(battery_note_sensor.entity_id, "20", attributes)
    await hass.async_block_till_done()
    assert len(events) == 3
    action.assert_awaited_once()

    remove()
    hass.states.async_set(battery_note_sensor.entity_id, "5", attributes)
    await hass.async_block_till_done()
    hass.states.async_set(battery_note_sensor.entity_id, "10", attributes)
    await hass.async_block_till_done()
    assert len(events) == 5
    action.assert_awaited_once()


@pytest.mark.parametrize(
    "reminder",
    [pytest.param(False, id="transition"), pytest.param(True, id="reminder")],
)
async def test_recovery_ignores_low_events(hass: HomeAssistant, reminder: bool) -> None:
    """Test low transitions and reminders never fire the recovery trigger."""
    action, remove = await _attach_trigger(hass, {}, RECOVERY_TRIGGER_KEY)
    hass.bus.async_fire(
        EVENT_BATTERY_THRESHOLD,
        {ATTR_BATTERY_LOW: True, ATTR_BATTERY_THRESHOLD_REMINDER: reminder},
    )
    await hass.async_block_till_done()
    action.assert_not_called()
    remove()


@pytest.mark.parametrize(
    "reminder",
    [pytest.param(False, id="transition"), pytest.param(True, id="reminder")],
)
@pytest.mark.parametrize(
    "option",
    [
        pytest.param("exclude", id="exclude"),
        pytest.param("only", id="only"),
        pytest.param("all", id="all"),
    ],
)
async def test_low_ignores_recovery_events(
    hass: HomeAssistant, reminder: bool, option: str
) -> None:
    """Test healthy battery events never trigger, regardless of reminder filtering."""
    action, remove = await _attach_trigger(
        hass, {"options": {"reminder": option}}, LOW_TRIGGER_KEY
    )
    hass.bus.async_fire(
        EVENT_BATTERY_THRESHOLD,
        {ATTR_BATTERY_LOW: False, ATTR_BATTERY_THRESHOLD_REMINDER: reminder},
    )
    await hass.async_block_till_done()
    action.assert_not_called()
    remove()


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({"target": {"entity_id": "invalid"}}, id="invalid-entity"),
        pytest.param({"options": {"reminder": "invalid"}}, id="invalid-reminder"),
        pytest.param({"options": {"reminder": True}}, id="boolean-reminder"),
        pytest.param({"options": {"for": 10}}, id="unsupported-option"),
    ],
)
async def test_invalid_low_config(hass: HomeAssistant, config: dict[str, Any]) -> None:
    """Test invalid low battery targets and reminder options are rejected."""
    with pytest.raises(vol.Invalid):
        await async_validate_trigger_config(
            hass, [{"platform": LOW_TRIGGER_KEY, **config}]
        )


async def test_low_trigger_description(
    hass: HomeAssistant, battery_note_config_entry: MockConfigEntry
) -> None:
    """Test Home Assistant loads the low trigger targets and reminder selector."""
    await setup_integration(hass, battery_note_config_entry)
    descriptions = await async_get_all_descriptions(hass)
    assert descriptions[LOW_TRIGGER_KEY] == {
        "target": {"entity": [{"integration": "battery_notes"}]},
        "fields": {
            "reminder": {
                "default": "all",
                "selector": {
                    "select": {
                        "translation_key": "battery_low_reminder",
                        "options": ["exclude", "only", "all"],
                        "custom_value": False,
                        "multiple": False,
                        "sort": False,
                    }
                },
            }
        },
    }


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({"target": {"entity_id": "invalid"}}, id="invalid-entity"),
        pytest.param({"target": {}, "options": {"for": 10}}, id="unsupported-option"),
        pytest.param({"options": {"reminder": "all"}}, id="unsupported-reminder"),
    ],
)
@pytest.mark.parametrize(
    "trigger_key",
    [
        pytest.param(TRIGGER_KEY, id="replacement"),
        pytest.param(RECOVERY_TRIGGER_KEY, id="recovery"),
    ],
)
async def test_invalid_config(
    hass: HomeAssistant, config: dict[str, Any], trigger_key: str
) -> None:
    """Test invalid target and option configurations are rejected."""
    with pytest.raises(vol.Invalid):
        await async_validate_trigger_config(hass, [{"platform": trigger_key, **config}])


@pytest.mark.parametrize(
    "trigger_key",
    [
        pytest.param(TRIGGER_KEY, id="replacement"),
        pytest.param(RECOVERY_TRIGGER_KEY, id="recovery"),
    ],
)
async def test_trigger_description(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    trigger_key: str,
) -> None:
    """Test Home Assistant loads the trigger's target selector definition."""
    await setup_integration(hass, battery_note_config_entry)

    descriptions = await async_get_all_descriptions(hass)

    assert descriptions[trigger_key] == {
        "fields": {},
        "target": {"entity": [{"integration": "battery_notes"}]},
    }

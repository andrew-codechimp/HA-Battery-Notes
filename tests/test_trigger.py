"""Tests for Battery Notes event triggers."""

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
import voluptuous as vol
from custom_components.battery_notes.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_DEVICE_ID,
    ATTR_PREVIOUS_BATTERY_LEVEL,
    ATTR_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_INCREASED,
    EVENT_BATTERY_NOT_REPLACED,
    EVENT_BATTERY_NOT_REPORTED,
    EVENT_BATTERY_REPLACED,
    EVENT_BATTERY_THRESHOLD,
    SERVICE_BATTERY_REPLACED,
    SERVICE_CHECK_BATTERY_LAST_REPLACED,
    SERVICE_CHECK_BATTERY_LAST_REPORTED,
    SERVICE_CHECK_BATTERY_LOW,
    SERVICE_DATA_DATE_TIME_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPORTED,
    SERVICE_DATA_RAISE_EVENTS,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
)

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
    label_registry as lr,
)
from homeassistant.helpers.trigger import (
    async_get_all_descriptions,
    async_initialize_triggers,
    async_validate_trigger_config,
)

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

TRIGGER_KEY = "battery_notes.battery_was_replaced"
INCREASED_TRIGGER_KEY = "battery_notes.battery_has_increased"
LOW_TRIGGER_KEY = "battery_notes.battery_became_low"
RECOVERY_TRIGGER_KEY = "battery_notes.battery_no_longer_low"
NOT_REPORTED_TRIGGER_KEY = "battery_notes.battery_was_not_reported"
NOT_REPLACED_TRIGGER_KEY = "battery_notes.battery_was_not_replaced"
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
async def battery_targets(
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
async def test_trigger_targets(
    hass: HomeAssistant,
    battery_note_source: str,
    battery_targets: dict[str, dict[str, str | list[str]]],
    target_kind: str,
    expected_by_source: dict[str, int],
) -> None:
    """Test shared target resolution across source types without duplicate runs."""
    action, remove = await _attach_trigger(
        hass, {"target": battery_targets[target_kind]}
    )
    events = async_capture_events(hass, EVENT_BATTERY_REPLACED)

    await hass.services.async_call(
        "button", "press", battery_targets["diagnostic-entity"], blocking=True
    )
    await hass.async_block_till_done()

    assert len(events) == 1
    assert action.await_count == expected_by_source[battery_note_source]
    remove()


async def test_replacement_actions_payload_and_cleanup(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_targets: dict[str, dict[str, str | list[str]]],
) -> None:
    """Test an omitted target forwards each action/button event until removed."""
    action, remove = await _attach_trigger(hass, {})
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
    await hass.services.async_call(
        "button", "press", battery_targets["diagnostic-entity"], blocking=True
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

    await hass.services.async_call(
        "button", "press", battery_targets["diagnostic-entity"], blocking=True
    )
    await hass.async_block_till_done()
    assert len(events) == 3
    assert action.await_count == 2


@pytest.mark.parametrize(
    "target_kind",
    [pytest.param("area", id="area"), pytest.param("entity-label", id="label")],
)
async def test_target_membership_changes(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_targets: dict[str, dict[str, str | list[str]]],
    target_kind: str,
) -> None:
    """Test targets resolve current registry membership for every event."""
    action, remove = await _attach_trigger(
        hass, {"target": battery_targets[target_kind]}
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


@pytest.mark.parametrize(
    ("target_kind", "other_source"),
    [
        pytest.param("note-entity", "", id="note-target-device-event"),
        pytest.param(
            "note-entity", "sensor.other_battery", id="note-target-sibling-event"
        ),
        pytest.param(
            "source-entity", "sensor.other_battery", id="source-target-sibling-event"
        ),
    ],
)
@pytest.mark.parametrize("battery_note_source", [pytest.param("entity", id="entity")])
@pytest.mark.parametrize(
    ("trigger_key", "event_type", "battery_low"),
    [
        pytest.param(TRIGGER_KEY, EVENT_BATTERY_REPLACED, True, id="replacement"),
        pytest.param(
            INCREASED_TRIGGER_KEY, EVENT_BATTERY_INCREASED, False, id="increased"
        ),
        pytest.param(LOW_TRIGGER_KEY, EVENT_BATTERY_THRESHOLD, True, id="low"),
        pytest.param(
            RECOVERY_TRIGGER_KEY, EVENT_BATTERY_THRESHOLD, False, id="recovery"
        ),
        pytest.param(
            NOT_REPORTED_TRIGGER_KEY,
            EVENT_BATTERY_NOT_REPORTED,
            False,
            id="not-reported",
        ),
        pytest.param(
            NOT_REPLACED_TRIGGER_KEY,
            EVENT_BATTERY_NOT_REPLACED,
            False,
            id="not-replaced",
        ),
    ],
)
async def test_entity_note_does_not_match_other_note_on_device(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_targets: dict[str, dict[str, str | list[str]]],
    trigger_key: str,
    event_type: str,
    battery_low: bool,
    other_source: str,
    target_kind: str,
) -> None:
    """Test every trigger isolates an entity note from other notes on its device."""
    action, remove = await _attach_trigger(
        hass, {"target": battery_targets[target_kind]}, trigger_key
    )
    coordinator = next(
        iter(battery_note_config_entry.runtime_data.subentry_coordinators.values())
    )
    data = coordinator.event_data(
        {ATTR_BATTERY_LOW: battery_low, ATTR_BATTERY_THRESHOLD_REMINDER: False}
    )
    hass.bus.async_fire(event_type, {**data, ATTR_SOURCE_ENTITY_ID: other_source})
    await hass.async_block_till_done()

    action.assert_not_called()

    hass.bus.async_fire(event_type, data)
    await hass.async_block_till_done()

    action.assert_awaited_once()
    remove()


async def test_events_only_run_the_corresponding_trigger(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test all six listeners coexist without running for another trigger's event."""
    await setup_integration(hass, mock_config_entry)
    events = {
        TRIGGER_KEY: (EVENT_BATTERY_REPLACED, False),
        INCREASED_TRIGGER_KEY: (EVENT_BATTERY_INCREASED, False),
        LOW_TRIGGER_KEY: (EVENT_BATTERY_THRESHOLD, True),
        RECOVERY_TRIGGER_KEY: (EVENT_BATTERY_THRESHOLD, False),
        NOT_REPORTED_TRIGGER_KEY: (EVENT_BATTERY_NOT_REPORTED, False),
        NOT_REPLACED_TRIGGER_KEY: (EVENT_BATTERY_NOT_REPLACED, False),
    }
    triggers = {key: await _attach_trigger(hass, {}, key) for key in events}
    expected_calls = dict.fromkeys(events, 0)

    for key, (event_type, battery_low) in events.items():
        hass.bus.async_fire(
            event_type,
            {ATTR_BATTERY_LOW: battery_low, ATTR_BATTERY_THRESHOLD_REMINDER: False},
        )
        await hass.async_block_till_done()
        expected_calls[key] += 1
        assert {
            key: action.await_count for key, (action, _) in triggers.items()
        } == expected_calls

    for _, remove in triggers.values():
        remove()


@pytest.mark.parametrize(
    ("options", "transition_count", "expected_event_indices"),
    [
        pytest.param({}, 1, [0, 1], id="default"),
        pytest.param(
            {"event_types": "low_state_transitions"}, 1, [0], id="low-state-transitions"
        ),
        pytest.param({"event_types": "reminders"}, 0, [1], id="reminders"),
        pytest.param({"event_types": "all"}, 1, [0, 1], id="all"),
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


@pytest.mark.parametrize(
    ("trigger_key", "event_type", "service", "days_field", "description"),
    [
        pytest.param(
            NOT_REPORTED_TRIGGER_KEY,
            EVENT_BATTERY_NOT_REPORTED,
            SERVICE_CHECK_BATTERY_LAST_REPORTED,
            SERVICE_DATA_DAYS_LAST_REPORTED,
            "battery was not reported",
            id="not-reported",
        ),
        pytest.param(
            NOT_REPLACED_TRIGGER_KEY,
            EVENT_BATTERY_NOT_REPLACED,
            SERVICE_CHECK_BATTERY_LAST_REPLACED,
            SERVICE_DATA_DAYS_LAST_REPLACED,
            "battery was not replaced",
            id="not-replaced",
        ),
    ],
)
async def test_check_action_triggers_and_cleanup(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    trigger_key: str,
    event_type: str,
    service: str,
    days_field: str,
    description: str,
) -> None:
    """Test checks own the limits and events, while triggers forward each payload."""
    await setup_integration(hass, battery_note_config_entry)
    action, remove = await _attach_trigger(hass, {}, trigger_key)
    events = async_capture_events(hass, event_type)

    await hass.services.async_call(DOMAIN, service, {days_field: 30}, blocking=True)
    await hass.async_block_till_done()
    assert events == []
    action.assert_not_called()

    freezer.tick(timedelta(days=31))
    await hass.async_block_till_done()
    assert events == []
    action.assert_not_called()

    response = await hass.services.async_call(
        DOMAIN,
        service,
        {days_field: 30, SERVICE_DATA_RAISE_EVENTS: False},
        blocking=True,
        return_response=True,
    )
    assert response is not None
    assert len(response[service]) == 1
    assert events == []
    action.assert_not_called()

    await hass.services.async_call(DOMAIN, service, {days_field: 31}, blocking=True)
    await hass.async_block_till_done()
    assert events == []
    action.assert_not_called()

    for _ in range(2):
        await hass.services.async_call(DOMAIN, service, {days_field: 30}, blocking=True)
        await hass.async_block_till_done()

    assert len(events) == 2
    assert action.await_count == 2
    for call, event in zip(action.call_args_list, events, strict=True):
        assert call.args[0]["trigger"] == {
            "id": "replaced",
            "idx": "0",
            "alias": None,
            "platform": trigger_key,
            "description": description,
            **event.data,
        }
        assert call.args[1] is event.context

    remove()
    await hass.services.async_call(DOMAIN, service, {days_field: 30}, blocking=True)
    await hass.async_block_till_done()
    assert len(events) == 3
    assert action.await_count == 2


async def test_increased_levels_payload_and_cleanup(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
) -> None:
    """Test the increase threshold, event payload, replacement date, and cleanup."""
    await setup_integration(hass, battery_note_config_entry)
    action, remove = await _attach_trigger(hass, {}, INCREASED_TRIGGER_KEY)
    events = async_capture_events(hass, EVENT_BATTERY_INCREASED)
    coordinator = next(
        iter(battery_note_config_entry.runtime_data.subentry_coordinators.values())
    )
    last_replaced = coordinator.last_replaced
    source_state = hass.states.get(battery_note_sensor.entity_id)
    assert source_state is not None
    attributes = source_state.attributes
    action.assert_not_called()

    hass.states.async_set(battery_note_sensor.entity_id, "40", attributes)
    await hass.async_block_till_done()
    hass.states.async_set(battery_note_sensor.entity_id, "64", attributes)
    await hass.async_block_till_done()
    assert events == []
    action.assert_not_called()

    hass.states.async_set(battery_note_sensor.entity_id, "89", attributes)
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data[ATTR_BATTERY_LEVEL] == 89
    assert events[0].data[ATTR_PREVIOUS_BATTERY_LEVEL] == 64
    assert ATTR_BATTERY_THRESHOLD_REMINDER not in events[0].data
    assert coordinator.last_replaced == last_replaced
    action.assert_awaited_once()
    assert action.call_args.args[0]["trigger"] == {
        "id": "replaced",
        "idx": "0",
        "alias": None,
        "platform": INCREASED_TRIGGER_KEY,
        "description": "battery has increased",
        **events[0].data,
    }
    assert action.call_args.args[1] is events[0].context

    hass.states.async_set(battery_note_sensor.entity_id, "89", attributes)
    await hass.async_block_till_done()
    hass.states.async_set(battery_note_sensor.entity_id, "60", attributes)
    await hass.async_block_till_done()
    assert len(events) == 1
    action.assert_awaited_once()

    remove()
    hass.states.async_set(battery_note_sensor.entity_id, "85", attributes)
    await hass.async_block_till_done()
    assert len(events) == 2
    action.assert_awaited_once()


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
    "config",
    [
        pytest.param({"target": {"entity_id": "invalid"}}, id="invalid-entity"),
        pytest.param({"options": {"event_types": "invalid"}}, id="invalid-event-types"),
        pytest.param({"options": {"event_types": True}}, id="boolean-event-types"),
        pytest.param({"options": {"for": 10}}, id="unsupported-option"),
    ],
)
async def test_invalid_low_config(hass: HomeAssistant, config: dict[str, Any]) -> None:
    """Test invalid low battery targets and reminder options are rejected."""
    with pytest.raises(vol.Invalid):
        await async_validate_trigger_config(
            hass, [{"platform": LOW_TRIGGER_KEY, **config}]
        )


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({}, id="omitted-options"),
        pytest.param({"options": {}}, id="empty-options"),
    ],
)
async def test_low_event_types_defaults_to_all(
    hass: HomeAssistant, config: dict[str, Any]
) -> None:
    """Test validation fills the required event types field with its default."""
    validated = await async_validate_trigger_config(
        hass, [{"platform": LOW_TRIGGER_KEY, **config}]
    )
    assert validated[0]["options"] == {"event_types": "all"}


async def test_low_trigger_description(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test Home Assistant loads the low trigger targets and event types selector."""
    await setup_integration(hass, mock_config_entry)
    descriptions = await async_get_all_descriptions(hass)
    description = descriptions[LOW_TRIGGER_KEY]
    assert description["target"] == {
        "entity": [{"integration": "battery_notes"}],
    }
    assert set(description["fields"]) == {"event_types"}
    field = description["fields"]["event_types"]
    assert field["default"] == "all"
    assert field["required"] is True
    selector = field["selector"]["select"]
    assert selector["translation_key"] == "battery_low_event_types"
    assert selector["options"] == ["all", "low_state_transitions", "reminders"]


@pytest.mark.parametrize(
    "config",
    [
        pytest.param({"target": {"entity_id": "invalid"}}, id="invalid-entity"),
        pytest.param({"target": {}, "options": {"for": 10}}, id="unsupported-option"),
        pytest.param({"options": {"event_types": "all"}}, id="unsupported-event-types"),
    ],
)
@pytest.mark.parametrize(
    "trigger_key",
    [
        pytest.param(TRIGGER_KEY, id="replacement"),
        pytest.param(INCREASED_TRIGGER_KEY, id="increased"),
        pytest.param(RECOVERY_TRIGGER_KEY, id="recovery"),
        pytest.param(NOT_REPORTED_TRIGGER_KEY, id="not-reported"),
        pytest.param(NOT_REPLACED_TRIGGER_KEY, id="not-replaced"),
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
        pytest.param(INCREASED_TRIGGER_KEY, id="increased"),
        pytest.param(RECOVERY_TRIGGER_KEY, id="recovery"),
        pytest.param(NOT_REPORTED_TRIGGER_KEY, id="not-reported"),
        pytest.param(NOT_REPLACED_TRIGGER_KEY, id="not-replaced"),
    ],
)
async def test_trigger_description(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    trigger_key: str,
) -> None:
    """Test Home Assistant loads the trigger's target selector definition."""
    await setup_integration(hass, mock_config_entry)

    descriptions = await async_get_all_descriptions(hass)

    assert descriptions[trigger_key] == {
        "fields": {},
        "target": {"entity": [{"integration": "battery_notes"}]},
    }

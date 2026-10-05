"""Tests for battery threshold and increased events driven by source states."""

from dataclasses import replace
from types import MappingProxyType

import pytest
from custom_components.battery_notes.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_PREVIOUS_BATTERY_LEVEL,
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_INCREASED,
    EVENT_BATTERY_THRESHOLD,
    SUBENTRY_BATTERY_NOTE,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_DEVICE_ID,
    PERCENTAGE,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")


@pytest.fixture(autouse=True)
def freeze_setup_time(freezer: FrozenDateTimeFactory) -> None:
    """Keep source creation and battery-report timestamps stable."""
    freezer.move_to("2026-01-01T12:00:00+00:00")


def _note_entry(
    mock_config_entry: MockConfigEntry, subentry: ConfigSubentry
) -> MockConfigEntry:
    """Create the parent entry holding a single battery note."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=mock_config_entry.version,
        title=mock_config_entry.title,
        data=mock_config_entry.data,
        options=mock_config_entry.options,
        subentries_data=[subentry.as_dict()],
    )


def _battery_low_entity_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    """Return the battery low binary sensor of the entry's battery note."""
    subentry = next(iter(entry.subentries.values()))
    entity_id = er.async_get(hass).async_get_entity_id(
        "binary_sensor", DOMAIN, f"{subentry.unique_id}_battery_low"
    )
    assert entity_id is not None
    return entity_id


def _summary(events: list[Event]) -> list[tuple[str, bool]]:
    """Summarise events as (event type, battery low) in firing order."""
    return [(event.event_type, event.data[ATTR_BATTERY_LOW]) for event in events]


async def _set_level(hass: HomeAssistant, entity_id: str, state: str) -> None:
    """Report a new state for the source battery percentage sensor."""
    hass.states.async_set(
        entity_id,
        state,
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
def battery_events(hass: HomeAssistant) -> list[Event]:
    """Capture threshold and increased events in firing order."""
    events: list[Event] = []

    @callback
    def _capture(event: Event) -> None:
        events.append(event)

    for event_type in (EVENT_BATTERY_THRESHOLD, EVENT_BATTERY_INCREASED):
        hass.bus.async_listen(event_type, _capture)
    return events


async def test_percentage_threshold_and_increase(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_events: list[Event],
) -> None:
    """Test events fire when the level crosses the low threshold or increases."""
    await setup_integration(hass, battery_note_config_entry)
    battery_low_id = _battery_low_entity_id(hass, battery_note_config_entry)

    # Dropping while staying above the default threshold of 10
    await _set_level(hass, battery_note_sensor.entity_id, "40")
    assert battery_events == []

    # Crossing below the threshold
    await _set_level(hass, battery_note_sensor.entity_id, "5")
    assert _summary(battery_events) == [(EVENT_BATTERY_THRESHOLD, True)]
    assert battery_events[0].data[ATTR_BATTERY_LEVEL] == 5
    assert battery_events[0].data[ATTR_PREVIOUS_BATTERY_LEVEL] == 40
    assert battery_events[0].data[ATTR_BATTERY_THRESHOLD_REMINDER] is False
    assert hass.states.get(battery_low_id).state == STATE_ON

    # Staying below the threshold
    await _set_level(hass, battery_note_sensor.entity_id, "4")
    assert len(battery_events) == 1

    # Replaced battery, back above the threshold and increased by the default of 25
    await _set_level(hass, battery_note_sensor.entity_id, "50")
    assert _summary(battery_events) == [
        (EVENT_BATTERY_THRESHOLD, True),
        (EVENT_BATTERY_THRESHOLD, False),
        (EVENT_BATTERY_INCREASED, False),
    ]
    for event in battery_events[1:]:
        assert event.data[ATTR_BATTERY_LEVEL] == 50
        assert event.data[ATTR_PREVIOUS_BATTERY_LEVEL] == 4
    assert hass.states.get(battery_low_id).state == STATE_OFF


@pytest.mark.parametrize("unavailable_state", [STATE_UNAVAILABLE, STATE_UNKNOWN])
async def test_percentage_unavailable_source(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_events: list[Event],
    unavailable_state: str,
) -> None:
    """Test an unavailable source fires no events and battery low follows it again."""
    await setup_integration(hass, battery_note_config_entry)
    battery_low_id = _battery_low_entity_id(hass, battery_note_config_entry)

    await _set_level(hass, battery_note_sensor.entity_id, "5")
    assert _summary(battery_events) == [(EVENT_BATTERY_THRESHOLD, True)]

    await _set_level(hass, battery_note_sensor.entity_id, unavailable_state)
    assert len(battery_events) == 1

    # Reporting the same low level again is not a new threshold crossing
    await _set_level(hass, battery_note_sensor.entity_id, "5")
    assert len(battery_events) == 1
    assert hass.states.get(battery_low_id).state == STATE_ON


@pytest.mark.parametrize(
    ("mock_config_entry", "report"),
    [
        pytest.param({}, ("45", []), id="defaults-no-event"),
        pytest.param(
            {CONF_DEFAULT_BATTERY_LOW_THRESHOLD: 50},
            ("45", [(EVENT_BATTERY_THRESHOLD, True)]),
            id="low-threshold-option",
        ),
        pytest.param({}, ("70", []), id="defaults-small-increase"),
        pytest.param(
            {CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD: 10},
            ("70", [(EVENT_BATTERY_INCREASED, False)]),
            id="increase-threshold-option",
        ),
    ],
    indirect=["mock_config_entry"],
)
@pytest.mark.parametrize("battery_note_source", ["device"])
async def test_default_threshold_options(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_events: list[Event],
    report: tuple[str, list[tuple[str, bool]]],
) -> None:
    """Test notes without their own thresholds use the integration defaults."""
    level, expected = report
    await setup_integration(hass, battery_note_config_entry)

    await _set_level(hass, battery_note_sensor.entity_id, level)

    assert _summary(battery_events) == expected


@pytest.fixture(params=["device", "standalone-entity"])
def binary_note_entry(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    battery_note_device: dr.DeviceEntry,
    mock_config_entry: MockConfigEntry,
    request: pytest.FixtureRequest,
) -> tuple[MockConfigEntry, str]:
    """Create a note for a source that only reports a battery low binary sensor."""
    source = entity_registry.async_get_or_create(
        "binary_sensor",
        "test",
        "door-battery-low",
        suggested_object_id="door_battery_low",
        original_device_class=BinarySensorDeviceClass.BATTERY,
        device_id=battery_note_device.id if request.param == "device" else None,
    )
    hass.states.async_set(
        source.entity_id,
        STATE_OFF,
        {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.BATTERY},
    )
    source_data = (
        {CONF_DEVICE_ID: battery_note_device.id}
        if request.param == "device"
        else {CONF_SOURCE_ENTITY_ID: source.entity_id}
    )
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                **source_data,
                CONF_BATTERY_TYPE: "CR2032",
                CONF_BATTERY_QUANTITY: 1,
                CONF_ADVANCED_SETTINGS: {},
            }
        ),
        subentry_id="binary-note-subentry",
        subentry_type=SUBENTRY_BATTERY_NOTE,
        title="Door battery low note",
        unique_id="bn_door_battery_low",
    )
    return _note_entry(mock_config_entry, subentry), source.entity_id


async def test_binary_source_events(
    hass: HomeAssistant,
    binary_note_entry: tuple[MockConfigEntry, str],
    battery_events: list[Event],
) -> None:
    """Test a binary source fires events only when its low state changes."""
    entry, source_id = binary_note_entry
    await setup_integration(hass, entry)
    battery_low_id = _battery_low_entity_id(hass, entry)
    attributes = {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.BATTERY}

    hass.states.async_set(source_id, STATE_ON, attributes)
    await hass.async_block_till_done()
    assert _summary(battery_events) == [(EVENT_BATTERY_THRESHOLD, True)]
    assert hass.states.get(battery_low_id).state == STATE_ON

    # An attribute-only update is not a new threshold crossing
    hass.states.async_set(source_id, STATE_ON, {**attributes, "voltage": 2.4})
    await hass.async_block_till_done()
    assert len(battery_events) == 1

    hass.states.async_set(source_id, STATE_UNAVAILABLE, attributes)
    await hass.async_block_till_done()
    assert len(battery_events) == 1

    hass.states.async_set(source_id, STATE_OFF, attributes)
    await hass.async_block_till_done()
    assert _summary(battery_events) == [
        (EVENT_BATTERY_THRESHOLD, True),
        (EVENT_BATTERY_THRESHOLD, False),
        (EVENT_BATTERY_INCREASED, False),
    ]
    assert hass.states.get(battery_low_id).state == STATE_OFF


@pytest.fixture
def template_note_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_battery_note_subentry: ConfigSubentry,
) -> MockConfigEntry:
    """Create a note whose low state comes from a template."""
    hass.states.async_set("input_boolean.door_battery_low", STATE_OFF)
    subentry = replace(
        mock_battery_note_subentry,
        data=MappingProxyType(
            {
                **mock_battery_note_subentry.data,
                CONF_ADVANCED_SETTINGS: {
                    CONF_BATTERY_LOW_TEMPLATE: "{{ is_state('input_boolean.door_battery_low', 'on') }}",
                },
            }
        ),
    )
    return _note_entry(mock_config_entry, subentry)


@pytest.mark.parametrize("battery_note_source", ["device"])
async def test_low_template_events(
    hass: HomeAssistant,
    template_note_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_events: list[Event],
) -> None:
    """Test a low template drives events and the percentage level doesn't."""
    await setup_integration(hass, template_note_entry)
    battery_low_id = _battery_low_entity_id(hass, template_note_entry)

    # The level is ignored for battery low when a template is configured
    await _set_level(hass, battery_note_sensor.entity_id, "5")
    assert battery_events == []

    hass.states.async_set("input_boolean.door_battery_low", STATE_ON)
    await hass.async_block_till_done()
    assert _summary(battery_events) == [(EVENT_BATTERY_THRESHOLD, True)]
    assert hass.states.get(battery_low_id).state == STATE_ON

    # Re-rendering to the same result is not a new threshold crossing
    hass.states.async_set("input_boolean.door_battery_low", STATE_ON, {"icon": "x"})
    await hass.async_block_till_done()
    assert len(battery_events) == 1

    hass.states.async_set("input_boolean.door_battery_low", STATE_OFF)
    await hass.async_block_till_done()
    assert _summary(battery_events) == [
        (EVENT_BATTERY_THRESHOLD, True),
        (EVENT_BATTERY_THRESHOLD, False),
        (EVENT_BATTERY_INCREASED, False),
    ]
    assert hass.states.get(battery_low_id).state == STATE_OFF

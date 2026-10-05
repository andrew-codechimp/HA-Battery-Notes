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
    CONF_BATTERY_PERCENTAGE_TEMPLATE,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_FILTER_OUTLIERS,
    CONF_RETAIN_STATE,
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


def _battery_plus_entity_id(hass: HomeAssistant, entry: MockConfigEntry) -> str:
    """Return the battery plus sensor of the entry's battery note."""
    subentry = next(iter(entry.subentries.values()))
    entity_id = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{subentry.unique_id}_battery_plus"
    )
    assert entity_id is not None
    return entity_id


def _summary(events: list[Event]) -> list[tuple[str, bool]]:
    """Summarise events as (event type, battery low) in firing order."""
    return [(event.event_type, event.data[ATTR_BATTERY_LOW]) for event in events]


def _levels(events: list[Event]) -> list[tuple[float, float]]:
    """Return the (level, previous level) of each event in firing order."""
    return [
        (event.data[ATTR_BATTERY_LEVEL], event.data[ATTR_PREVIOUS_BATTERY_LEVEL])
        for event in events
    ]


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
    """Test an unavailable source fires no events and makes the entities unavailable."""
    await setup_integration(hass, battery_note_config_entry)
    battery_low_id = _battery_low_entity_id(hass, battery_note_config_entry)
    battery_plus_id = _battery_plus_entity_id(hass, battery_note_config_entry)

    await _set_level(hass, battery_note_sensor.entity_id, "5")
    assert _summary(battery_events) == [(EVENT_BATTERY_THRESHOLD, True)]

    await _set_level(hass, battery_note_sensor.entity_id, unavailable_state)
    assert len(battery_events) == 1
    assert hass.states.get(battery_low_id).state == STATE_UNAVAILABLE
    assert hass.states.get(battery_plus_id).state == STATE_UNAVAILABLE

    # Reporting the same low level again is not a new threshold crossing
    await _set_level(hass, battery_note_sensor.entity_id, "5")
    assert len(battery_events) == 1
    assert hass.states.get(battery_low_id).state == STATE_ON
    assert hass.states.get(battery_plus_id).state == "5.0"


@pytest.mark.parametrize("unavailable_state", [STATE_UNAVAILABLE, STATE_UNKNOWN])
async def test_percentage_renamed_source_availability(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_events: list[Event],
    unavailable_state: str,
) -> None:
    """Test battery low follows availability after its source is renamed."""
    await setup_integration(hass, battery_note_config_entry)
    battery_low_id = _battery_low_entity_id(hass, battery_note_config_entry)
    source_id = "sensor.renamed_door_battery"
    er.async_get(hass).async_update_entity(
        battery_note_sensor.entity_id, new_entity_id=source_id
    )
    await hass.async_block_till_done()

    await _set_level(hass, source_id, "5")
    assert hass.states.get(battery_low_id).state == STATE_ON
    assert _summary(battery_events) == [(EVENT_BATTERY_THRESHOLD, True)]

    await _set_level(hass, source_id, unavailable_state)
    assert hass.states.get(battery_low_id).state == STATE_UNAVAILABLE
    assert len(battery_events) == 1

    await _set_level(hass, source_id, "5")
    assert hass.states.get(battery_low_id).state == STATE_ON
    assert len(battery_events) == 1


@pytest.mark.parametrize("battery_note_source", ["device"])
async def test_percentage_unavailable_source_retain_state(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_battery_note_subentry: ConfigSubentry,
    battery_note_sensor: er.RegistryEntry,
) -> None:
    """Test entities keep their last state for an unavailable source with retain state."""
    entry = _note_entry(
        mock_config_entry,
        replace(
            mock_battery_note_subentry,
            data=MappingProxyType(
                {
                    **mock_battery_note_subentry.data,
                    CONF_ADVANCED_SETTINGS: {CONF_RETAIN_STATE: True},
                }
            ),
        ),
    )
    await setup_integration(hass, entry)
    battery_low_id = _battery_low_entity_id(hass, entry)
    battery_plus_id = _battery_plus_entity_id(hass, entry)

    await _set_level(hass, battery_note_sensor.entity_id, "5")
    await _set_level(hass, battery_note_sensor.entity_id, STATE_UNAVAILABLE)

    assert hass.states.get(battery_low_id).state == STATE_ON
    assert hass.states.get(battery_plus_id).state == "5.0"


@pytest.mark.parametrize("unavailable_state", [STATE_UNAVAILABLE, STATE_UNKNOWN])
async def test_percentage_unavailable_source_disabled_battery_plus(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_events: list[Event],
    unavailable_state: str,
) -> None:
    """Test battery low recovers without an enabled Battery Plus sensor."""
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{subentry.unique_id}_battery_plus",
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    await setup_integration(hass, battery_note_config_entry)
    battery_low_id = _battery_low_entity_id(hass, battery_note_config_entry)
    battery_plus_id = _battery_plus_entity_id(hass, battery_note_config_entry)
    assert hass.states.get(battery_plus_id) is None
    assert hass.states.get(battery_low_id).state == STATE_OFF

    await _set_level(hass, battery_note_sensor.entity_id, unavailable_state)
    assert hass.states.get(battery_low_id).state == STATE_UNAVAILABLE

    await _set_level(hass, battery_note_sensor.entity_id, "55")
    assert hass.states.get(battery_low_id).state == STATE_OFF
    assert battery_events == []


@pytest.fixture(params=[False, True], ids=["default", "retain-state"])
def percentage_template_note_entry(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_battery_note_subentry: ConfigSubentry,
    request: pytest.FixtureRequest,
) -> MockConfigEntry:
    """Create a note whose level comes from a percentage template."""
    hass.states.async_set("sensor.template_battery", "40")
    subentry = replace(
        mock_battery_note_subentry,
        data=MappingProxyType(
            {
                **mock_battery_note_subentry.data,
                CONF_ADVANCED_SETTINGS: {
                    CONF_BATTERY_PERCENTAGE_TEMPLATE: "{{ states('sensor.template_battery') }}",
                    CONF_RETAIN_STATE: request.param,
                },
            }
        ),
    )
    return _note_entry(mock_config_entry, subentry)


@pytest.mark.parametrize("battery_note_source", ["device"])
async def test_percentage_template_unavailable_source(
    hass: HomeAssistant,
    percentage_template_note_entry: MockConfigEntry,
) -> None:
    """Test an unavailable percentage template source follows retain state."""
    entry = percentage_template_note_entry
    await setup_integration(hass, entry)
    battery_plus_id = _battery_plus_entity_id(hass, entry)
    battery_low_id = _battery_low_entity_id(hass, entry)
    coordinator = next(iter(entry.runtime_data.subentry_coordinators.values()))
    assert hass.states.get(battery_plus_id).state == "40.0"
    assert hass.states.get(battery_low_id).state == STATE_OFF

    hass.states.async_set("sensor.template_battery", STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    if coordinator.retain_state:
        assert hass.states.get(battery_plus_id).state == "40.0"
        assert hass.states.get(battery_low_id).state == STATE_OFF
    else:
        assert hass.states.get(battery_plus_id).state == STATE_UNAVAILABLE
        assert hass.states.get(battery_low_id).state == STATE_UNAVAILABLE


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
    assert hass.states.get(battery_low_id).state == STATE_UNAVAILABLE

    hass.states.async_set(source_id, STATE_OFF, attributes)
    await hass.async_block_till_done()
    assert _summary(battery_events) == [
        (EVENT_BATTERY_THRESHOLD, True),
        (EVENT_BATTERY_THRESHOLD, False),
        (EVENT_BATTERY_INCREASED, False),
    ]
    # Nominal levels follow the direction of the battery low change
    assert _levels(battery_events) == [(0, 100), (100, 0), (100, 0)]
    assert hass.states.get(battery_low_id).state == STATE_OFF


@pytest.mark.parametrize(
    ("source_state", "expected_low"),
    [
        pytest.param(STATE_ON, True, id="on"),
        pytest.param(STATE_OFF, False, id="off"),
    ],
)
async def test_binary_source_coordinator_refresh(
    hass: HomeAssistant,
    binary_note_entry: tuple[MockConfigEntry, str],
    battery_events: list[Event],
    source_state: str,
    expected_low: bool,
) -> None:
    """Test startup and independent refreshes preserve the source binary state."""
    entry, source_id = binary_note_entry
    hass.states.async_set(
        source_id, source_state, {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.BATTERY}
    )
    await setup_integration(hass, entry)
    battery_low_id = _battery_low_entity_id(hass, entry)
    assert hass.states.get(battery_low_id).state == source_state
    subentry = next(iter(entry.subentries.values()))
    coordinator = entry.runtime_data.subentry_coordinators[subentry.subentry_id]
    assert coordinator.battery_low_binary_state is expected_low
    events_before_refresh = list(battery_events)

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(battery_low_id).state == source_state
    assert coordinator.battery_low_binary_state is expected_low
    assert battery_events == events_before_refresh


@pytest.mark.parametrize(
    "unavailable_state",
    [
        pytest.param(STATE_UNAVAILABLE, id="unavailable"),
        pytest.param(STATE_UNKNOWN, id="unknown"),
    ],
)
async def test_binary_source_unavailable_coordinator_refresh(
    hass: HomeAssistant,
    binary_note_entry: tuple[MockConfigEntry, str],
    battery_events: list[Event],
    unavailable_state: str,
) -> None:
    """Test refreshes keep an unavailable source unavailable despite a stored low state."""
    entry, source_id = binary_note_entry
    attributes = {ATTR_DEVICE_CLASS: BinarySensorDeviceClass.BATTERY}
    hass.states.async_set(source_id, STATE_ON, attributes)
    await setup_integration(hass, entry)
    battery_low_id = _battery_low_entity_id(hass, entry)
    assert hass.states.get(battery_low_id).state == STATE_ON
    subentry = next(iter(entry.subentries.values()))
    coordinator = entry.runtime_data.subentry_coordinators[subentry.subentry_id]

    hass.states.async_set(source_id, unavailable_state, attributes)
    await hass.async_block_till_done()
    assert coordinator.battery_low_binary_state is True
    assert hass.states.get(battery_low_id).state == STATE_UNAVAILABLE
    events_before_refresh = list(battery_events)

    await coordinator.async_refresh()
    await hass.async_block_till_done()

    assert hass.states.get(battery_low_id).state == STATE_UNAVAILABLE
    assert coordinator.battery_low_binary_state is True
    assert battery_events == events_before_refresh


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
    # Nominal levels follow the direction of the battery low change
    assert _levels(battery_events) == [(0, 100), (100, 0), (100, 0)]
    assert hass.states.get(battery_low_id).state == STATE_OFF


@pytest.fixture
def outlier_note_entry(
    mock_config_entry: MockConfigEntry, mock_battery_note_subentry: ConfigSubentry
) -> MockConfigEntry:
    """Create a note with the outlier filter enabled."""
    return _note_entry(
        mock_config_entry,
        replace(
            mock_battery_note_subentry,
            data=MappingProxyType(
                {
                    **mock_battery_note_subentry.data,
                    CONF_ADVANCED_SETTINGS: {CONF_FILTER_OUTLIERS: True},
                }
            ),
        ),
    )


@pytest.mark.parametrize("battery_note_source", ["device"])
async def test_outlier_filter_rejects_consecutive_outliers(
    hass: HomeAssistant,
    outlier_note_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_events: list[Event],
) -> None:
    """Test consecutive outliers are rejected until they make up the window."""
    await setup_integration(hass, outlier_note_entry)
    battery_plus_id = _battery_plus_entity_id(hass, outlier_note_entry)
    for level in ("95", "90"):
        await _set_level(hass, battery_note_sensor.entity_id, level)
    battery_events.clear()

    # A second outlier is not allowed through by comparing it with the first one
    for level in ("5", "6"):
        await _set_level(hass, battery_note_sensor.entity_id, level)
        assert hass.states.get(battery_plus_id).state == "90.0"
    assert battery_events == []

    # Once low readings make up most of the window they are accepted
    await _set_level(hass, battery_note_sensor.entity_id, "7")
    assert hass.states.get(battery_plus_id).state == "7.0"
    assert _summary(battery_events) == [(EVENT_BATTERY_THRESHOLD, True)]


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(
            (("40", "30"), "0.0", [(EVENT_BATTERY_THRESHOLD, True)]), id="draining"
        ),
        pytest.param((("95", "90"), "90.0", []), id="glitch"),
    ],
)
@pytest.mark.parametrize("battery_note_source", ["device"])
async def test_outlier_filter_zero_level(
    hass: HomeAssistant,
    outlier_note_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    battery_events: list[Event],
    case: tuple[tuple[str, str], str, list[tuple[str, bool]]],
) -> None:
    """Test a 0% reading is accepted when the battery drains, not as a glitch."""
    history, expected_state, expected_events = case
    await setup_integration(hass, outlier_note_entry)
    battery_plus_id = _battery_plus_entity_id(hass, outlier_note_entry)
    for level in history:
        await _set_level(hass, battery_note_sensor.entity_id, level)
    battery_events.clear()

    await _set_level(hass, battery_note_sensor.entity_id, "0")

    assert hass.states.get(battery_plus_id).state == expected_state
    assert _summary(battery_events) == expected_events

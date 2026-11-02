"""Test source placeholders through real Battery Notes template entities."""

from datetime import timedelta
from logging import ERROR

import pytest
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_BATTERY_PERCENTAGE_TEMPLATE,
    CONF_RETAIN_STATE,
    DOMAIN,
    EVENT_BATTERY_INCREASED,
    EVENT_BATTERY_THRESHOLD,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.selector import TemplateSelector
from homeassistant.util import dt as dt_util

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

PERCENTAGE_TEMPLATE = "{{ states('[[source::sensor:battery:%]]') }}"
VOLTAGE_TEMPLATE = "{{ states('[[source::sensor:voltage:V]]') | float / 3 * 100 }}"


def _template_entity_id(
    entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    domain: Platform = Platform.SENSOR,
    suffix: str = "battery_plus",
) -> str:
    """Find the generated entity by its stable unique ID."""
    subentry = next(iter(entry.subentries.values()))
    entity_id = entity_registry.async_get_entity_id(
        domain, DOMAIN, f"{subentry.unique_id}_{suffix}"
    )
    assert entity_id is not None
    return entity_id


@pytest.fixture
def battery_note_source() -> str:
    """Use a device unless a test explicitly varies the source arrangement."""
    return "device"


@pytest.mark.parametrize(
    ("battery_note_source", "source_template_entry"),
    [
        pytest.param(
            "device",
            PERCENTAGE_TEMPLATE,
            id="device",
        ),
        pytest.param(
            "entity",
            '{{ states("[[SoUrCe::SeNsOr:BaTtErY:PeRcEnTaGe]]") }}',
            id="entity-mixed-case",
        ),
        pytest.param(
            "standalone-entity",
            "{{ state_attr('[[source::sensor:battery]]', 'unit_of_measurement') == '%' and states('[[SOURCE::SENSOR:BATTERY:percentage]]') }}",
            id="standalone-multiple-placeholders",
        ),
    ],
    indirect=["source_template_entry"],
)
async def test_source_template_updates(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Resolve all note types without matching the generated Battery+ entity."""
    subentry = next(iter(source_template_entry.subentries.values()))
    template = subentry.data[CONF_ADVANCED_SETTINGS][CONF_BATTERY_PERCENTAGE_TEMPLATE]
    assert TemplateSelector()(template) == template
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == "55.0"

    freezer.tick(timedelta(hours=1))
    hass.states.async_set(
        battery_note_sensor.entity_id,
        "25",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.BATTERY,
            ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE,
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "25.0"
    assert (
        subentry.data[CONF_ADVANCED_SETTINGS][CONF_BATTERY_PERCENTAGE_TEMPLATE]
        == template
    )


@pytest.mark.parametrize("battery_note_source", ["entity"])
async def test_source_template_rename_and_disable(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Rebind a renamed source and recover when it is enabled again."""
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    source = entity_registry.async_update_entity(
        battery_note_sensor.entity_id, new_entity_id="sensor.renamed_battery"
    )
    hass.states.async_set(
        source.entity_id, "20", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "20.0"

    entity_registry.async_update_entity(
        source.entity_id, disabled_by=er.RegistryEntryDisabler.USER
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    entity_registry.async_update_entity(
        source.entity_id, disabled_by=None, hidden_by=er.RegistryEntryHider.USER
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "20.0"


@pytest.mark.parametrize(
    ("source_template_entry", "expected_state"),
    [
        pytest.param(
            {
                CONF_BATTERY_PERCENTAGE_TEMPLATE: PERCENTAGE_TEMPLATE,
                CONF_RETAIN_STATE: False,
            },
            STATE_UNAVAILABLE,
            id="unavailable",
        ),
        pytest.param(
            {
                CONF_BATTERY_PERCENTAGE_TEMPLATE: PERCENTAGE_TEMPLATE,
                CONF_RETAIN_STATE: True,
            },
            "55.0",
            id="retain-state",
        ),
    ],
    indirect=["source_template_entry"],
)
async def test_source_template_ambiguity_recovers(  # noqa: PLR0913
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
    expected_state: str,
) -> None:
    """Reject multiple matches and recover when the extra candidate is removed."""
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    extra = entity_registry.async_get_or_create(
        Platform.SENSOR,
        "test",
        "extra_battery",
        device_id=battery_note_device.id,
        original_device_class=SensorDeviceClass.BATTERY,
        unit_of_measurement=PERCENTAGE,
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == expected_state
    assert "Ambiguous source placeholder" in caplog.text

    entity_registry.async_remove(extra.entity_id)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "55.0"


@pytest.mark.parametrize(
    ("source_template_entry", "message"),
    [
        pytest.param(
            "{{ states('[[source::sensor:battery:V]]') }}",
            "No entity matches",
            id="wrong-unit",
        ),
        pytest.param(
            "{{ states('[[source::binary_sensor:battery]]') }}",
            "No entity matches",
            id="wrong-domain",
        ),
        pytest.param(
            "{{ states('[[source::switch:battery]]') }}",
            "Invalid source placeholder",
            id="invalid-domain",
        ),
        pytest.param(
            "{{ states('[[source::sensor:battery:]]') }}",
            "Invalid source placeholder",
            id="empty-unit",
        ),
        pytest.param(
            "{{ states('prefix_[[source::sensor:battery]]') }}",
            "whole quoted entity ID",
            id="partial-string",
        ),
        pytest.param(
            "{{ states('[[TARGET::Sensor:Battery]]') }}",
            "Unsupported placeholder scope",
            id="unsupported-scope",
        ),
        pytest.param(
            "{{ states('[[SOURCE:Sensor:Battery:%]]') }}",
            "[[namespace::selector]]",
            id="single-colon-namespace",
        ),
        pytest.param(
            "{{ states('[[source::sensor::battery::%]]') }}",
            "Invalid source placeholder",
            id="double-colon-selector-fields",
        ),
    ],
    indirect=["source_template_entry"],
)
async def test_source_template_errors(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
    message: str,
) -> None:
    """Resolution failures make the template unavailable with a specific error."""
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    assert message in caplog.text


@pytest.mark.parametrize(
    "source_template_entry",
    [VOLTAGE_TEMPLATE],
    indirect=True,
)
async def test_source_template_late_metadata(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Retry missing matches as entities and their live metadata arrive."""
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    voltage = entity_registry.async_get_or_create(
        Platform.SENSOR,
        "test",
        "battery_voltage",
        device_id=battery_note_device.id,
    )
    hass.states.async_set(
        voltage.entity_id,
        "2.4",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
            ATTR_UNIT_OF_MEASUREMENT: "mV",
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    hass.states.async_set(
        voltage.entity_id,
        "2.4",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
            ATTR_UNIT_OF_MEASUREMENT: "V",
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "80.0"

    hass.states.async_set(
        voltage.entity_id,
        "2400",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
            ATTR_UNIT_OF_MEASUREMENT: "mV",
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    assert not [record for record in caplog.records if record.exc_info]


@pytest.mark.parametrize("battery_note_source", ["entity"])
@pytest.mark.parametrize(
    "source_template_entry",
    [VOLTAGE_TEMPLATE],
    indirect=True,
)
async def test_source_template_device_reassociation(  # noqa: PLR0913
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Follow the source entity's current device instead of the saved device ID."""
    other_device = device_registry.async_get_or_create(
        config_entry_id=next(iter(battery_note_device.config_entries)),
        identifiers={("test", "other-device")},
    )
    for device, value in ((battery_note_device, "3"), (other_device, "2.4")):
        voltage = entity_registry.async_get_or_create(
            Platform.SENSOR,
            "test",
            f"voltage-{device.id}",
            device_id=device.id,
            original_device_class=SensorDeviceClass.VOLTAGE,
            unit_of_measurement="V",
        )
        hass.states.async_set(voltage.entity_id, value)
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == "100.0"

    entity_registry.async_update_entity(
        battery_note_sensor.entity_id, device_id=other_device.id
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "80.0"

    entity_registry.async_update_entity(battery_note_sensor.entity_id, device_id=None)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE


@pytest.mark.parametrize("battery_note_source", ["entity"])
async def test_source_template_entity_rename(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Restart source resolution when the Battery+ entity itself is renamed."""
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    source = entity_registry.async_update_entity(
        battery_note_sensor.entity_id, new_entity_id="sensor.renamed_source"
    )
    hass.states.async_set(
        source.entity_id, "55", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    await hass.async_block_till_done()
    entity_registry.async_update_entity(
        entity_id, new_entity_id="sensor.renamed_battery_plus"
    )
    await hass.async_block_till_done()
    freezer.tick(timedelta(hours=1))
    hass.states.async_set(
        source.entity_id, "30", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    await hass.async_block_till_done()
    assert hass.states.get("sensor.renamed_battery_plus").state == "30.0"


@pytest.mark.parametrize("battery_note_source", ["entity"])
@pytest.mark.parametrize(
    "source_template_entry",
    [{CONF_BATTERY_LOW_TEMPLATE: "{{ states('[[SoUrCe::BiNaRy_SeNsOr:BaTtErY]]') }}"}],
    indirect=True,
)
async def test_binary_source_template(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Preserve binary low semantics and unavailable states."""
    source = entity_registry.async_get_or_create(
        Platform.BINARY_SENSOR,
        "test",
        "battery_low",
        device_id=battery_note_device.id,
        original_device_class=BinarySensorDeviceClass.BATTERY,
    )
    hass.states.async_set(source.entity_id, STATE_ON)
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(
        source_template_entry, entity_registry, Platform.BINARY_SENSOR, "battery_low"
    )
    assert hass.states.get(entity_id).state == STATE_ON

    hass.states.async_set(source.entity_id, STATE_UNAVAILABLE)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    hass.states.async_set(source.entity_id, STATE_OFF)
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_OFF


async def test_source_template_unload(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Stop template and source-resolution listeners on unload."""
    await setup_integration(hass, source_template_entry)
    coordinator = next(
        iter(source_template_entry.runtime_data.subentry_coordinators.values())
    )
    assert float(coordinator.current_battery_level) == 55
    assert await hass.config_entries.async_unload(source_template_entry.entry_id)
    await hass.async_block_till_done()

    entity_registry.async_update_entity(
        battery_note_sensor.entity_id, new_entity_id="sensor.removed_note_source"
    )
    hass.states.async_set(
        "sensor.removed_note_source", "5", {ATTR_UNIT_OF_MEASUREMENT: PERCENTAGE}
    )
    await hass.async_block_till_done()
    assert float(coordinator.current_battery_level) == 55


@pytest.mark.parametrize(
    "source_template_entry",
    [
        pytest.param(
            "{# [[source::sensor:voltage:V]] #}{{ 55 }}",
            id="comment-only",
        ),
        pytest.param(
            "{# {{ states('[[source::sensor:voltage:V]]') }} #}{% set example %}{% raw %}'[[source::sensor:voltage:V]]'{% endraw %} '[[source::sensor:voltage:V]]'{% endset %}{{ states('[[source::sensor:battery:%]]') }}",
            id="comments-raw-and-text",
        ),
        pytest.param(
            "{# '[[source::sensor:battery:%]]' #}\r\n  {%- set example = 1 -%}\r\n{{ states('[[source::sensor:battery:%]]') }}\r\n",
            id="whitespace-control",
        ),
    ],
    indirect=True,
)
async def test_source_template_ignores_inactive_content(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Only actual Jinja string tokens participate in source resolution."""
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == "55.0"
    assert "Unable to resolve source template" not in caplog.text


@pytest.mark.parametrize(
    ("source_template_entry", "source_template_voltage"),
    [
        pytest.param(
            "{{ states('[[source::sensor:voltage:V]]') | float * 10 }}",
            "v",
            id="lowercase-source",
        ),
        pytest.param(
            "{{ states('[[source::sensor:voltage:MV]]') | float * 10 }}",
            "mV",
            id="uppercase-selector",
        ),
    ],
    indirect=True,
)
@pytest.mark.usefixtures("source_template_voltage")
async def test_source_template_unit_case(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Match units regardless of case on either side of the comparison."""
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == "24.0"


@pytest.mark.parametrize(
    "source_template_entry",
    ["{{ states('[[SOURCE::SENSOR:PM25]]') }}"],
    indirect=True,
)
async def test_source_template_device_class_digits(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Accept device classes containing digits and mixed-case registry metadata."""
    source = entity_registry.async_get_or_create(
        Platform.SENSOR,
        "test",
        "particulate",
        device_id=battery_note_device.id,
        original_device_class=SensorDeviceClass.PM25,
    )
    entity_registry.async_update_entity(source.entity_id, device_class="Pm25")
    hass.states.async_set(source.entity_id, "25")
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == "25.0"


@pytest.mark.parametrize(
    "source_template_entry",
    ["{{ states('[[source::sensor:voltage:V]]') | float / 3 * 100 + now().minute }}"],
    indirect=True,
)
async def test_source_template_rebind_timer_cleanup(  # noqa: PLR0913
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    source_template_voltage: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Avoid stale errors, false transitions, and revived timers during rebinding."""
    freezer.move_to("2026-01-01T12:00:00+00:00")
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == "80.0"
    increased = async_capture_events(hass, EVENT_BATTERY_INCREASED)
    thresholds = async_capture_events(hass, EVENT_BATTERY_THRESHOLD)

    hass.states.async_set(
        source_template_voltage.entity_id,
        "2400",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
            ATTR_UNIT_OF_MEASUREMENT: "mV",
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE
    assert increased == []
    assert thresholds == []

    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == STATE_UNAVAILABLE

    hass.states.async_set(
        source_template_voltage.entity_id,
        "2.4",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
            ATTR_UNIT_OF_MEASUREMENT: "V",
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "81.0"
    assert await hass.config_entries.async_unload(source_template_entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=1))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert not [record for record in caplog.records if record.exc_info]
    assert not [
        record
        for record in caplog.records
        if record.levelno >= ERROR and record.name.startswith("homeassistant")
    ]


@pytest.mark.parametrize(
    "source_template_entry",
    [VOLTAGE_TEMPLATE],
    indirect=True,
)
@pytest.mark.usefixtures("delayed_source_template_refresh")
async def test_source_template_pending_refresh_unload(
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    source_template_voltage: er.RegistryEntry,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Cancel a pending refresh without allowing an old tracker to update state."""
    await setup_integration(hass, source_template_entry)
    coordinator = next(
        iter(source_template_entry.runtime_data.subentry_coordinators.values())
    )
    assert float(coordinator.current_battery_level) == 80
    hass.states.async_set(
        source_template_voltage.entity_id,
        "2400",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
            ATTR_UNIT_OF_MEASUREMENT: "mV",
        },
    )
    await hass.async_block_till_done()
    assert float(coordinator.current_battery_level) == 80
    assert await hass.config_entries.async_unload(source_template_entry.entry_id)
    await hass.async_block_till_done()
    freezer.tick(timedelta(minutes=2))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert float(coordinator.current_battery_level) == 80
    assert not [record for record in caplog.records if record.exc_info]


@pytest.mark.parametrize(
    "source_template_entry",
    [VOLTAGE_TEMPLATE],
    indirect=True,
)
@pytest.mark.usefixtures("delayed_source_template_refresh")
async def test_source_template_coalesced_refresh(  # noqa: PLR0913
    hass: HomeAssistant,
    source_template_entry: MockConfigEntry,
    source_template_voltage: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Apply the latest reading when metadata recovers before a pending refresh."""
    await setup_integration(hass, source_template_entry)
    entity_id = _template_entity_id(source_template_entry, entity_registry)
    assert hass.states.get(entity_id).state == "80.0"
    increased = async_capture_events(hass, EVENT_BATTERY_INCREASED)

    hass.states.async_set(
        source_template_voltage.entity_id,
        "2400",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
            ATTR_UNIT_OF_MEASUREMENT: "mV",
        },
    )
    await hass.async_block_till_done()
    hass.states.async_set(
        source_template_voltage.entity_id,
        "2.1",
        {
            ATTR_DEVICE_CLASS: SensorDeviceClass.VOLTAGE,
            ATTR_UNIT_OF_MEASUREMENT: "V",
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "80.0"

    freezer.tick(timedelta(minutes=2))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state == "70.0"
    assert increased == []
    assert not [record for record in caplog.records if record.exc_info]

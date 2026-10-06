"""Tests for Battery Notes registry helpers."""

from types import MappingProxyType

import pytest
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_HIDE_BATTERY,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    SUBENTRY_BATTERY_NOTE,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntryState, ConfigSubentry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")


@pytest.fixture
def hidden_batteries(
    hass: HomeAssistant, battery_note_device: dr.DeviceEntry
) -> dict[str, er.RegistryEntry]:
    """Register battery and protected entities on the same source device."""
    registry = er.async_get(hass)
    entities = {}
    for name, domain, device_class, hidden_by, platform, disabled_by in (
        (
            "battery",
            "sensor",
            SensorDeviceClass.BATTERY,
            er.RegistryEntryHider.INTEGRATION,
            "test",
            None,
        ),
        (
            "low",
            "binary_sensor",
            BinarySensorDeviceClass.BATTERY,
            er.RegistryEntryHider.INTEGRATION,
            "test",
            None,
        ),
        (
            "user_hidden",
            "sensor",
            SensorDeviceClass.BATTERY,
            er.RegistryEntryHider.USER,
            "test",
            None,
        ),
        (
            "temperature",
            "sensor",
            SensorDeviceClass.TEMPERATURE,
            er.RegistryEntryHider.INTEGRATION,
            "test",
            None,
        ),
        (
            "battery_plus",
            "sensor",
            SensorDeviceClass.BATTERY,
            er.RegistryEntryHider.INTEGRATION,
            DOMAIN,
            None,
        ),
        (
            "disabled",
            "sensor",
            SensorDeviceClass.BATTERY,
            er.RegistryEntryHider.INTEGRATION,
            "test",
            er.RegistryEntryDisabler.USER,
        ),
    ):
        entities[name] = registry.async_get_or_create(
            domain,
            platform,
            name,
            device_id=battery_note_device.id,
            original_device_class=device_class,
            hidden_by=hidden_by,
            disabled_by=disabled_by,
        )
    return entities


@pytest.mark.parametrize(
    ("selection", "unhidden"),
    [
        pytest.param("device", ("battery", "low", "disabled"), id="device"),
        pytest.param("entity", ("low",), id="entity"),
        pytest.param("missing-device", (), id="missing-device"),
        pytest.param("missing-entity", (), id="missing-entity"),
        pytest.param("no-source", (), id="no-source"),
    ],
)
async def test_remove_entry_unhides_source_batteries(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    hidden_batteries: dict[str, er.RegistryEntry],
    selection: str,
    unhidden: tuple[str, ...],
) -> None:
    """Test removing an entry only shows integration-hidden source batteries."""
    device_id = hidden_batteries["battery"].device_id
    source_data = {
        "device": {CONF_DEVICE_ID: device_id},
        "entity": {
            CONF_DEVICE_ID: device_id,
            CONF_SOURCE_ENTITY_ID: hidden_batteries["low"].entity_id,
        },
        "missing-device": {CONF_DEVICE_ID: "missing"},
        "missing-entity": {CONF_SOURCE_ENTITY_ID: "sensor.missing"},
        "no-source": {},
    }[selection]
    subentry = ConfigSubentry(
        subentry_type=SUBENTRY_BATTERY_NOTE,
        title="Battery note",
        unique_id="bn_battery",
        data=MappingProxyType(
            {
                **source_data,
                CONF_BATTERY_TYPE: "AA",
                CONF_BATTERY_QUANTITY: 1,
                CONF_ADVANCED_SETTINGS: {},
            }
        ),
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=mock_config_entry.version,
        data=mock_config_entry.data,
        options={**mock_config_entry.options, CONF_HIDE_BATTERY: True},
        subentries_data=[subentry.as_dict()],
    )
    expected = {
        **{name: entity.hidden_by for name, entity in hidden_batteries.items()},
        **dict.fromkeys(unhidden),
    }

    await setup_integration(hass, entry)
    assert entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    assert {
        name: registry.async_get(entity.entity_id).hidden_by
        for name, entity in hidden_batteries.items()
    } == expected
    assert (
        registry.async_get(hidden_batteries["disabled"].entity_id).disabled_by
        is er.RegistryEntryDisabler.USER
    )

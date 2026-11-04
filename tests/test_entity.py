"""Tests for entity naming and registry identity."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import ATTR_FRIENDLY_NAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
    floor_registry as fr,
)

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

PLUS_UNIQUE_ID = "bn_door_battery_battery_plus"
TYPE_UNIQUE_ID = "bn_door_battery_battery_type"


@pytest.mark.parametrize("battery_note_area", ["Hall"], indirect=True)
@pytest.mark.usefixtures("battery_note_area")
@pytest.mark.parametrize(
    ("parts", "expected_ids"),
    [
        pytest.param(
            [
                er.EntityNamePart.AREA,
                er.EntityNamePart.DEVICE,
                er.EntityNamePart.ENTITY,
            ],
            {
                "device": "sensor.hall_door_sensor_battery_plus",
                "entity": "sensor.hall_door_sensor_battery_battery_plus",
                "standalone-entity": "sensor.door_battery_note_battery_plus",
            },
            id="area-device-entity",
        ),
        pytest.param(
            [er.EntityNamePart.ENTITY, er.EntityNamePart.DEVICE],
            {
                "device": "sensor.battery_plus_door_sensor",
                "entity": "sensor.battery_battery_plus_door_sensor",
                "standalone-entity": "sensor.door_battery_note_battery_plus",
            },
            id="entity-device",
        ),
        pytest.param(
            [er.EntityNamePart.ENTITY],
            {
                "device": "sensor.battery_plus",
                "entity": "sensor.battery_battery_plus",
                "standalone-entity": "sensor.door_battery_note_battery_plus",
            },
            id="entity-only",
        ),
    ],
)
async def test_preferred_entity_id_format(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_source: str,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    device_registry: dr.DeviceRegistry,
    entity_registry: er.EntityRegistry,
    parts: list[er.EntityNamePart],
    expected_ids: dict[str, str],
) -> None:
    """Generate IDs from preferences without taking ownership of the source device."""
    entity_registry.async_update_settings(entity_id_parts=parts)
    device_before = device_registry.async_get(battery_note_device.id)
    await setup_integration(hass, battery_note_config_entry)

    entity_id = entity_registry.async_get_entity_id(
        "sensor", "battery_notes", PLUS_UNIQUE_ID
    )
    assert entity_id == expected_ids[battery_note_source]
    entry = entity_registry.async_get(entity_id)
    assert entry is not None
    assert entry.suggested_object_id is None
    assert entry.device_id == battery_note_sensor.device_id
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.attributes["friendly_name"].endswith("Battery+")
    assert device_registry.async_get(battery_note_device.id) == device_before


@pytest.mark.parametrize("battery_note_area", ["Hall"], indirect=True)
@pytest.mark.usefixtures("battery_note_area")
@pytest.mark.parametrize(
    ("existing_object_id", "name", "expected_ids"),
    [
        pytest.param(
            "old_battery_plus",
            None,
            {
                "device": "sensor.hall_door_sensor_battery_plus",
                "entity": "sensor.hall_door_sensor_battery_battery_plus",
                "standalone-entity": "sensor.door_battery_note_battery_plus",
            },
            id="integration-generated",
        ),
        pytest.param(
            "my_custom_id",
            "My battery",
            {
                "device": "sensor.hall_door_sensor_my_battery",
                "entity": "sensor.hall_door_sensor_my_battery",
                "standalone-entity": "sensor.my_battery",
            },
            id="user-customized",
        ),
    ],
)
async def test_existing_entity_id_and_regeneration(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_source: str,
    battery_note_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    existing_object_id: str,
    name: str | None,
    expected_ids: dict[str, str],
) -> None:
    """Keep existing IDs and customizations until the user explicitly regenerates."""
    battery_note_config_entry.add_to_hass(hass)
    original = entity_registry.async_get_or_create(
        "sensor",
        "battery_notes",
        PLUS_UNIQUE_ID,
        config_entry=battery_note_config_entry,
        config_subentry_id="battery-note-subentry",
        device_id=battery_note_sensor.device_id,
        suggested_object_id=existing_object_id,
    )
    entity_registry.async_update_entity(
        original.entity_id,
        name=name,
        icon="mdi:leaf",
        hidden_by=er.RegistryEntryHider.USER,
    )
    assert await hass.config_entries.async_setup(battery_note_config_entry.entry_id)
    await hass.async_block_till_done()
    assert await hass.config_entries.async_reload(battery_note_config_entry.entry_id)
    await hass.async_block_till_done()

    entry = entity_registry.async_get(original.entity_id)
    assert entry is not None
    assert entry.id == original.id
    assert entry.unique_id == original.unique_id
    assert entry.name == name
    assert entry.icon == "mdi:leaf"
    assert entry.hidden_by is er.RegistryEntryHider.USER
    assert entry.suggested_object_id is None
    assert hass.states.get(original.entity_id) is not None

    new_entity_id = entity_registry.async_regenerate_entity_id(entry)
    assert new_entity_id == expected_ids[battery_note_source]
    entity_registry.async_update_entity(entry.entity_id, new_entity_id=new_entity_id)
    await hass.async_block_till_done()
    assert hass.states.get(original.entity_id) is None
    assert hass.states.get(new_entity_id) is not None
    assert entity_registry.async_get(new_entity_id).id == original.id


@pytest.mark.parametrize("battery_note_source", ["entity"], indirect=True)
@pytest.mark.parametrize(
    ("original_name", "has_entity_name", "name", "expected_id"),
    [
        pytest.param(
            "Left channel",
            True,
            None,
            "sensor.door_sensor_left_channel_battery_type",
            id="entity-name",
        ),
        pytest.param(
            "Door sensor Left channel",
            False,
            None,
            "sensor.door_sensor_left_channel_battery_type",
            id="legacy-name",
        ),
        pytest.param(
            "Door sensor",
            False,
            None,
            "sensor.door_sensor_battery_type",
            id="legacy-device-name",
        ),
        pytest.param(
            None, True, None, "sensor.door_sensor_battery_type", id="device-name"
        ),
        pytest.param(
            "Battery",
            True,
            "Left channel",
            "sensor.door_sensor_left_channel_battery_type",
            id="user-name",
        ),
        pytest.param(
            "Battery", True, "", "sensor.door_sensor_battery_type", id="empty-user-name"
        ),
    ],
)
async def test_source_entity_name(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
    original_name: str | None,
    has_entity_name: bool,
    name: str | None,
    expected_id: str,
) -> None:
    """Use the source's own name without repeating its device name."""
    entity_registry.async_update_entity(
        battery_note_sensor.entity_id,
        original_name=original_name,
        has_entity_name=has_entity_name,
        name=name,
    )
    await setup_integration(hass, battery_note_config_entry)
    assert (
        entity_registry.async_get_entity_id("sensor", "battery_notes", TYPE_UNIQUE_ID)
        == expected_id
    )


@pytest.mark.parametrize("battery_note_source", ["device"], indirect=True)
async def test_device_name_and_id_collision(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Use the current device name and let HA resolve an occupied entity ID."""
    dr.async_get(hass).async_update_device(
        battery_note_device.id, name_by_user="Remote"
    )
    source = entity_registry.async_update_entity(
        battery_note_sensor.entity_id, new_entity_id="sensor.remote_battery"
    )
    occupied = entity_registry.async_get_or_create(
        "sensor",
        "test",
        "other-battery-plus",
        suggested_object_id="remote_battery_plus",
    )
    await setup_integration(hass, battery_note_config_entry)

    assert (
        entity_registry.async_get_entity_id("sensor", "battery_notes", PLUS_UNIQUE_ID)
        == "sensor.remote_battery_plus_2"
    )
    assert entity_registry.async_get(occupied.entity_id) == occupied
    assert entity_registry.async_get(source.entity_id) == source


@pytest.mark.parametrize(
    ("language", "plus_name", "low_name"),
    [
        pytest.param("de", "Batterie+", "Batterie fast leer", id="german"),
        pytest.param("fr", "Batterie+", "Batterie faible", id="french"),
        pytest.param("zh-Hans", " 电池 +", " 电池低电量", id="chinese"),
    ],
)
async def test_english_ids_with_translated_display_names(  # noqa: PLR0913
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_source: str,
    entity_registry: er.EntityRegistry,
    language: str,
    plus_name: str,
    low_name: str,
) -> None:
    """Keep English ID components while translating the displayed entity name."""
    hass.config.language = language
    entity_registry.async_update_settings(
        entity_id_parts=[er.EntityNamePart.ENTITY, er.EntityNamePart.DEVICE]
    )
    await setup_integration(hass, battery_note_config_entry)

    id_prefix, id_suffix, display_prefix = {
        "device": ("", "_door_sensor", "Door sensor "),
        "entity": ("battery_", "_door_sensor", "Door sensor Battery "),
        "standalone-entity": ("door_battery_note_", "", "Door battery note "),
    }[battery_note_source]
    for platform, unique_id, english_name, translated_name in (
        (Platform.SENSOR, PLUS_UNIQUE_ID, "battery_plus", plus_name),
        (
            Platform.BINARY_SENSOR,
            "bn_door_battery_battery_low",
            "battery_plus_low",
            low_name,
        ),
    ):
        entity_id = entity_registry.async_get_entity_id(
            platform, "battery_notes", unique_id
        )
        assert entity_id == f"{platform}.{id_prefix}{english_name}{id_suffix}"
        entry = entity_registry.async_get(entity_id)
        assert entry is not None
        assert entry.object_id_base == f"{id_prefix}{english_name}"
        assert entry.suggested_object_id is None
        state = hass.states.get(entity_id)
        assert state is not None
        assert (
            state.attributes[ATTR_FRIENDLY_NAME] == f"{display_prefix}{translated_name}"
        )


@pytest.mark.parametrize("battery_note_source", ["device"], indirect=True)
async def test_regenerate_battery_plus_low_id(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    entity_registry: er.EntityRegistry,
) -> None:
    """Keep the plus component when regenerating an existing low-battery ID."""
    floor = fr.async_get(hass).async_create("First floor")
    area_registry = ar.async_get(hass)
    area = area_registry.async_create("Andrew's office")
    area_registry.async_update(area.id, floor_id=floor.floor_id)
    dr.async_get(hass).async_update_device(
        battery_note_device.id, name_by_user="esphm5atomecho02", area_id=area.id
    )
    entity_registry.async_update_settings(
        entity_id_parts=[
            er.EntityNamePart.FLOOR,
            er.EntityNamePart.AREA,
            er.EntityNamePart.DEVICE,
            er.EntityNamePart.ENTITY,
        ]
    )
    battery_note_config_entry.add_to_hass(hass)
    original = entity_registry.async_get_or_create(
        Platform.BINARY_SENSOR,
        "battery_notes",
        "bn_door_battery_battery_low",
        config_entry=battery_note_config_entry,
        config_subentry_id="battery-note-subentry",
        device_id=battery_note_device.id,
        suggested_object_id="esphm5atomecho02_battery_plus_low",
    )
    assert await hass.config_entries.async_setup(battery_note_config_entry.entry_id)
    await hass.async_block_till_done()

    entry = entity_registry.async_get(original.entity_id)
    assert entry is not None
    assert entry.entity_id == "binary_sensor.esphm5atomecho02_battery_plus_low"
    assert entry.id == original.id
    assert entry.object_id_base == "battery_plus_low"
    assert entity_registry.async_regenerate_entity_id(entry) == (
        "binary_sensor.first_floor_andrew_s_office_esphm5atomecho02_battery_plus_low"
    )

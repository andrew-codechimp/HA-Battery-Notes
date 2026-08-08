"""Tests for Battery Notes sensor platform."""

from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.battery_notes.const import DOMAIN

from homeassistant.helpers import entity_registry as er

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry


async def test_battery_type_sensor_created(
    entity_registry: er.EntityRegistry,
    battery_note_subentry: ConfigSubentry,
) -> None:
    """Test that battery type sensor is created for device-based subentry."""
    expected_unique_id = f"{battery_note_subentry.unique_id}_battery_type"
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, expected_unique_id
    )

    assert entity_id is not None, (
        f"Battery type sensor with unique_id {expected_unique_id} was not created"
    )
    type_sensor_entity = entity_registry.async_get(entity_id)
    assert type_sensor_entity is not None
    assert type_sensor_entity.domain == "sensor"
    assert type_sensor_entity.platform == DOMAIN


async def test_battery_last_replaced_sensor_created(
    entity_registry: er.EntityRegistry,
    battery_note_subentry: ConfigSubentry,
) -> None:
    """Test that battery last replaced sensor is created for device subentry."""
    expected_unique_id = f"{battery_note_subentry.unique_id}_battery_last_replaced"
    entity_id = entity_registry.async_get_entity_id(
        "sensor", DOMAIN, expected_unique_id
    )

    assert entity_id is not None, (
        "Battery last replaced sensor with unique_id "
        f"{expected_unique_id} was not created"
    )
    last_replaced_sensor_entity = entity_registry.async_get(entity_id)
    assert last_replaced_sensor_entity is not None
    assert last_replaced_sensor_entity.domain == "sensor"
    assert last_replaced_sensor_entity.platform == DOMAIN

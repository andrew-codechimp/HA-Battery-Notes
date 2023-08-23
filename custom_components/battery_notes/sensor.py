"""Sensor platform for battery_notes."""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import BaseEntity
from .const import DOMAIN, CONF_BATTERY_TYPE, CONF_DEVICE_ID



async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""
    registry = er.async_get(hass)
    # entity_id = er.async_validate_entity_id(
    #     registry, config_entry.entry_id
    # )

    device_id = config_entry.data.get(CONF_DEVICE_ID)
    battery_type = config_entry.data.get(CONF_BATTERY_TYPE)

    async_add_entities(
        [
            BatteryType(
                hass,
                config_entry.title,
                SENSOR_DOMAIN,
                config_entry.entry_id,
                config_entry.entry_id,
                device_id,
            )
        ]
    )


class BatteryType(BaseEntity, SensorEntity):
    """Represents a battery type sensor."""

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return "A Battery"

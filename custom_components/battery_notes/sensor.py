"""Sensor platform for battery_notes."""
from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.helpers.event import async_track_state_change_event

from homeassistant.components.homeassistant import exposed_entities
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_UNAVAILABLE,
)

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
                device_id=device_id,
                battery_type=battery_type,
            )
        ]
    )

class BatteryType(BaseEntity, SensorEntity):
    """Represents a battery type sensor."""
    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_title: str,
        domain: str,
        entity_id: str,
        unique_id: str,
        device_id: str,
        battery_type: str,
    ) -> None:
        super().__init__(
            hass,
            config_entry_title,
            domain,
            entity_id,
            unique_id,
            device_id=device_id,
        )
        self.battery_type = battery_type

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        # return self.battery_type
        print ("Getting battery type")
        return self.battery_type

    async def async_added_to_hass(self) -> None:
        """Register callbacks and copy the wrapped entity's custom name if set."""

        @callback
        def _async_state_changed_listener(event: Event | None = None) -> None:
            """Handle child updates."""
            print("Here " + self.native_value)
            self.async_state_changed_listener(event)
            self.async_write_ha_state()
            self.async_schedule_update_ha_state()

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._battery_note_entity_id], _async_state_changed_listener
            )
        )

        # Call once on adding
        _async_state_changed_listener()

        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._battery_note_entity_id},
            )

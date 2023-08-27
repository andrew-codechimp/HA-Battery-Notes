"""Sensor platform for battery_notes."""
from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta
import logging
import voluptuous as vol

from homeassistant.components.sensor import (
    DOMAIN as SENSOR_DOMAIN,
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import config_validation as cv, device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_state_change_event,
)

from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    EventType,
    StateType,
)

from homeassistant.components.homeassistant import exposed_entities
from homeassistant.const import (
    CONF_NAME,
    CONF_TYPE,
    CONF_UNIQUE_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    ATTR_ENTITY_ID,
)

from . import PLATFORMS

from .const import (
    DOMAIN,
    CONF_BATTERY_TYPE,
    CONF_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)

ICON = "mdi:battery-unknown"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_BATTERY_TYPE): cv.string,
    }
)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""
    device_id = config_entry.data.get(CONF_DEVICE_ID)
    battery_type = config_entry.data.get(CONF_BATTERY_TYPE)

    async_add_entities(
        [
            BatteryTypeSensor(
                config_entry.title,
                config_entry.entry_id,
                device_id=device_id,
                battery_type=battery_type,
            )
        ]
    )

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the battery type sensor."""
    name: str | None = config.get(CONF_NAME)
    unique_id = config.get(CONF_UNIQUE_ID)
    device_id: str = config[CONF_DEVICE_ID]
    battery_type: str = config[CONF_BATTERY_TYPE]

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    async_add_entities(
        [BatteryTypeSensor(name, unique_id, device_id, battery_type)]
    )

class BatteryTypeSensor(SensorEntity):
    """Represents a battery type sensor."""
    _attr_icon = ICON
    _attr_should_poll = False

    def __init__(
        self,
        name: str,
        unique_id: str,
        device_id: str,
        battery_type: str,
    ) -> None:
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._device_id = device_id
        self._battery_type = battery_type

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._attr_unique_id], self._async_battery_type_state_changed_listener
            )
        )

        # Call once on adding
        self._async_battery_type_state_changed_listener()

        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._attr_unique_id},
            )

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        # return self.battery_type
        return self._battery_type

    @callback
    def _async_battery_type_state_changed_listener(self, event: Event | None = None) -> None:
        """Handle the sensor state changes."""
        self.async_write_ha_state()
        self.async_schedule_update_ha_state(True)

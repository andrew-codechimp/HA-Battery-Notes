"""Sensor platform for battery_types."""
from __future__ import annotations

import logging
import homeassistant.helpers.config_validation as cv
import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
import voluptuous as vol

from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_CONDITION,
    CONF_DOMAIN,
    CONF_ENTITIES,
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_UNIQUE_ID,
)
from .const import DOMAIN, LOGGER, CONF_DEVICE_ID, CONF_BATTERY_TYPE
from .entity import BatteryTypesEntity

ENTITY_DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery_types",
        name="Battery type",
        icon="mdi:battery-unknown",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

SENSOR_CONFIG = {
    vol.Optional(CONF_NAME): cv.string,
    vol.Optional(CONF_DEVICE_ID): cv.string,
    vol.Optional(CONF_BATTERY_TYPE): cv.string,
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_devices(
        BatteryTypesSensor(
            coordinator=coordinator,
            entity_description=entity_description,
        )
        for entity_description in ENTITY_DESCRIPTIONS
    )

async def attach_entities_to_source_device(
    config_entry: ConfigEntry | None,
    entities_to_add: list[Entity],
    hass: HomeAssistant,
    source_entity: SourceEntity,
) -> None:
    """Set the entity to same device as the source entity, if any available."""
    if source_entity.entity_entry and source_entity.device_entry:
        device_id = source_entity.device_entry.id
        device_registry = dr.async_get(hass)
        for entity in (
            entity for entity in entities_to_add if isinstance(entity, BaseEntity)
        ):
            try:
                entity.source_device_id = source_entity.device_entry.id  # type: ignore
            except AttributeError:  # pragma: no cover
                _LOGGER.error(f"{entity.entity_id}: Cannot set device id on entity")
        if (
            config_entry
            and config_entry.entry_id not in source_entity.device_entry.config_entries
        ):
            device_registry.async_update_device(
                device_id,
                add_config_entry_id=config_entry.entry_id,
            )

class BatteryTypesSensor(BatteryTypesEntity, SensorEntity):
    """battery_types Sensor class."""

    def __init__(
        self,
        coordinator: BatteryTypesDataUpdateCoordinator,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor class."""
        super().__init__(coordinator)
        self.entity_description = entity_description

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.data.get("body")
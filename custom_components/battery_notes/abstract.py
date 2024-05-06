"""Abstract methods for battery_notes."""
from __future__ import annotations

from dataclasses import dataclass

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from homeassistant.const import CONF_ENTITY_ID, CONF_NAME, CONF_UNIQUE_ID
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.core import HomeAssistant, split_entity_id, callback
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.typing import ConfigType

from .common import SourceEntity

from .const import (
    DOMAIN,
)

SENSOR_ENTITY_ID_FORMAT = SENSOR_DOMAIN + ".{}"
BINARY_SENSOR_ENTITY_ID_FORMAT = BINARY_SENSOR_DOMAIN + ".{}"
BUTTON_ENTITY_ID_FORMAT = BUTTON_DOMAIN + ".{}"

@callback
def generate_sensor_entity_id(
    hass: HomeAssistant,
    entity_config: ConfigType,
    name_suffix: str,
    source_entity: SourceEntity | None = None,
    name: str | None = None,
    unique_id: str | None = None,
) -> str:
    """Generates the entity_id to use for a sensor."""
    if entity_id := get_entity_id_by_unique_id(hass, SENSOR_DOMAIN, unique_id):
        return entity_id
    name_pattern = str("{} " + name_suffix)
    object_id = name or entity_config.get(CONF_NAME)
    if object_id is None and source_entity:
        object_id = source_entity.object_id
    return async_generate_entity_id(
        SENSOR_ENTITY_ID_FORMAT,
        name_pattern.format(object_id),
        hass=hass,
    )

@callback
def generate_binary_sensor_entity_id(
    hass: HomeAssistant,
    entity_config: ConfigType,
    name_suffix: str,
    source_entity: SourceEntity | None = None,
    name: str | None = None,
    unique_id: str | None = None,
) -> str:
    """Generates the entity_id to use for a binary sensor."""
    if entity_id := get_entity_id_by_unique_id(hass, BINARY_SENSOR_DOMAIN, unique_id):
        return entity_id
    name_pattern = str("{} " + name_suffix)
    object_id = name or entity_config.get(CONF_NAME)
    if object_id is None and source_entity:
        object_id = source_entity.object_id
    return async_generate_entity_id(
        BINARY_SENSOR_ENTITY_ID_FORMAT,
        name_pattern.format(object_id),
        hass=hass,
    )

@callback
def generate_button_entity_id(
    hass: HomeAssistant,
    entity_config: ConfigType,
    name_suffix: str,
    source_entity: SourceEntity | None = None,
    name: str | None = None,
    unique_id: str | None = None,
) -> str:
    """Generates the entity_id to use for a button."""
    if entity_id := get_entity_id_by_unique_id(hass, BUTTON_DOMAIN, unique_id):
        return entity_id
    name_pattern = str("{} " + name_suffix)
    object_id = name or entity_config.get(CONF_NAME)
    if object_id is None and source_entity:
        object_id = source_entity.object_id
    return async_generate_entity_id(
        BUTTON_ENTITY_ID_FORMAT,
        name_pattern.format(object_id),
        hass=hass,
    )

def get_entity_id_by_unique_id(
    hass: HomeAssistant,
    domain: str,
    unique_id: str | None,
) -> str | None:
    if unique_id is None:
        return None
    entity_reg = er.async_get(hass)
    return entity_reg.async_get_entity_id(domain, DOMAIN, unique_id)

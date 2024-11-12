"""Diagnostic helpers."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)

from .common import get_device_model_id
from .const import CONF_SOURCE_ENTITY_ID


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    device_id = config_entry.data.get(CONF_DEVICE_ID, None)
    source_entity_id = config_entry.data.get(CONF_SOURCE_ENTITY_ID, None)

    if source_entity_id:
        entity = entity_registry.async_get(source_entity_id)
        if entity:
            device_id = entity.device_id

    diagnostics = {"entry": config_entry.as_dict()}

    if device_id:
        device_entry = device_registry.async_get(device_id)
        if device_entry:
            device_info = {
                "manufacturer": device_entry.manufacturer,
                "model": device_entry.model,
                "model_id": get_device_model_id(device_entry),
                "hw_version": device_entry.hw_version,
            }
            diagnostics.update({"device": device_info})

    return diagnostics

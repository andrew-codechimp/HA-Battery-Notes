"""Custom integration to integrate BatteryNotes with Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-battery-notes
"""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from homeassistant.const import CONF_NAME

from .const import (
    DOMAIN,
    CONF_BATTERY_TYPE,
    CONF_SENSORS,
)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_update_entry))

    return True


async def async_update_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update a given config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

# async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
#     """Called after a config entry is removed."""
#     updated_entries: list[ConfigEntry] = []

#     sensor_type = config_entry.data.get(CONF_SENSOR_TYPE)
#     if sensor_type == SensorType.VIRTUAL_POWER:
#         updated_entries = await remove_power_sensor_from_associated_groups(
#             hass,
#             config_entry,
#         )
#     if sensor_type == SensorType.GROUP:
#         updated_entries = await remove_group_from_power_sensor_entry(hass, config_entry)

#     for entry in updated_entries:
#         if entry.state == ConfigEntryState.LOADED:
#             await hass.config_entries.async_reload(entry.entry_id)

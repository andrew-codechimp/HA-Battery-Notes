"""Custom integration to integrate BatteryNotes with Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-battery-notes
"""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.event import async_track_entity_registry_updated_event

from .const import CONF_DEVICE_ID

PLATFORMS = [Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    # registry = er.async_get(hass)
    # device_registry = dr.async_get(hass)

    # entity_id = entry.entry_id

    # async def async_registry_updated(event: Event) -> None:
    #     """Handle entity registry update."""
    #     data = event.data
    #     if data["action"] == "remove":
    #         await hass.config_entries.async_remove(entry.entry_id)

    #     if data["action"] != "update":
    #         return

    #     if "entity_id" in data["changes"]:
    #         # Entity_id changed, reload the config entry
    #         await hass.config_entries.async_reload(entry.entry_id)

    #     if device_id and "device_id" in data["changes"]:
    #         # If the tracked switch is no longer in the device, remove our config entry
    #         # from the device
    #         if (
    #             not (entity_entry := registry.async_get(data[CONF_ENTITY_ID]))
    #             or not device_registry.async_get(device_id)
    #             or entity_entry.device_id == device_id
    #         ):
    #             # No need to do any cleanup
    #             return

    #         device_registry.async_update_device(
    #             device_id, remove_config_entry_id=entry.entry_id
    #         )

    # entry.async_on_unload(
    #     async_track_entity_registry_updated_event(
    #         hass, entity_id, async_registry_updated
    #     )
    # )

    # device_id = async_add_to_device(hass, entry)

    await hass.config_entries.async_forward_entry_setups(
        entry, (Platform.SENSOR,)
    )

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True

@callback
async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)

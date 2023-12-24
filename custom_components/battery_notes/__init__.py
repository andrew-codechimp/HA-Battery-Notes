"""Custom integration to integrate BatteryNotes with Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-battery-notes
"""
from __future__ import annotations

import logging
from datetime import datetime, time
from dateutil import parser
from typing import cast

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from awesomeversion.awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import __version__ as HA_VERSION  # noqa: N812
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.service import (
    async_register_admin_service,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er


from .discovery import DiscoveryManager
from .library_coordinator import BatteryNotesLibraryUpdateCoordinator
from .library_updater import (
    LibraryUpdaterClient,
)
from .coordinator import BatteryNotesCoordinator
from .store import (
    BatteryNotesStorage,
    async_get_registry,
)

from .const import (
    DOMAIN,
    DOMAIN_CONFIG,
    PLATFORMS,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_LIBRARY,
    DATA_UPDATE_COORDINATOR,
    SERVICE_BATTERY_CHANGED,
    SERVICE_BATTERY_CHANGED_SCHEMA,
    DATA_STORE,
    DATA_COORDINATOR,
    ATTR_REMOVE,
)

MIN_HA_VERSION = "2023.7"

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            vol.Schema(
                {
                    vol.Optional(CONF_ENABLE_AUTODISCOVERY, default=True): cv.boolean,
                    vol.Optional(CONF_LIBRARY, default="library.json"): cv.string,
                },
            ),
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

ATTR_SERVICE_DEVICE_ID = "device_id"
ATTR_SERVICE_DATETIME_CHANGED = "datetime_changed"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Integration setup."""

    if AwesomeVersion(HA_VERSION) < AwesomeVersion(MIN_HA_VERSION):  # pragma: no cover
        msg = (
            "This integration requires at least HomeAssistant version "
            f" {MIN_HA_VERSION}, you are running version {HA_VERSION}."
            " Please upgrade HomeAssistant to continue use this integration."
        )
        _LOGGER.critical(msg)
        return False

    domain_config: ConfigType = config.get(DOMAIN) or {
        CONF_ENABLE_AUTODISCOVERY: True,
    }

    hass.data[DOMAIN] = {
        DOMAIN_CONFIG: domain_config,
    }

    store = await async_get_registry(hass)

    coordinator = BatteryNotesCoordinator(hass, store)
    hass.data[DOMAIN][DATA_COORDINATOR] = coordinator

    library_coordinator = BatteryNotesLibraryUpdateCoordinator(
        hass=hass,
        client=LibraryUpdaterClient(session=async_get_clientsession(hass)),
    )

    hass.data[DOMAIN][DATA_UPDATE_COORDINATOR] = library_coordinator

    await coordinator.async_refresh()

    if domain_config.get(CONF_ENABLE_AUTODISCOVERY):
        discovery_manager = DiscoveryManager(hass, config)
        await discovery_manager.start_discovery()
    else:
        _LOGGER.debug("Auto discovery disabled")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # Register custom services
    register_services(hass)

    return True

async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:

    if "device_id" not in config_entry.data:
        return

    device_id = config_entry.data["device_id"]

    coordinator = hass.data[DOMAIN][DATA_COORDINATOR]
    data = {
        ATTR_REMOVE : True
        }

    coordinator.async_update_device_config(device_id = device_id, data = data)

    _LOGGER.debug("Removed Device {}".format(device_id))

@callback
async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

@callback
def register_services(hass):
    """Register services used by battery notes component."""

    async def handle_battery_changed(call):
        """Handle the service call."""
        device_id = call.data.get(ATTR_SERVICE_DEVICE_ID, "")

        device_registry = dr.async_get(hass)

        device_entry = device_registry.async_get(device_id)
        if not device_entry:
            return

        for entry_id in device_entry.config_entries:
            if (
                (entry := hass.config_entries.async_get_entry(entry_id))
                and entry.domain == DOMAIN
            ):
                date_changed = call.data.get(ATTR_SERVICE_DATETIME_CHANGED, datetime.utcnow())

                coordinator = hass.data[DOMAIN][DATA_COORDINATOR]
                device_entry = {
                    "battery_last_changed" : date_changed
                    }

                coordinator.async_update_device_config(device_id = device_id, data = device_entry)

                await coordinator._async_update_data()
                await coordinator.async_request_refresh()

                _LOGGER.debug("Device {} battery changed on {}".format(device_id,str(date_changed)))

    hass.services.async_register(DOMAIN, SERVICE_BATTERY_CHANGED, handle_battery_changed, schema=SERVICE_BATTERY_CHANGED_SCHEMA)

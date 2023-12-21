"""Custom integration to integrate BatteryNotes with Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-battery-notes
"""
from __future__ import annotations

import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from awesomeversion.awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import __version__ as HA_VERSION  # noqa: N812
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from homeassistant.helpers.typing import ConfigType

from .discovery import DiscoveryManager
from .library_coordinator import BatteryNotesLibraryUpdateCoordinator
from .library_updater import (
    LibraryUpdaterClient,
)

from .const import (
    DOMAIN,
    DOMAIN_CONFIG,
    PLATFORMS,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_LIBRARY,
    DATA_UPDATE_COORDINATOR,
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

    coordinator = BatteryNotesLibraryUpdateCoordinator(
        hass=hass,
        client=LibraryUpdaterClient(session=async_get_clientsession(hass)),
    )

    hass.data[DOMAIN][DATA_UPDATE_COORDINATOR] = coordinator

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

"""Custom integration to integrate BatteryNotes with Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-battery-notes
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime

import voluptuous as vol
from awesomeversion.awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import __version__ as HA_VERSION  # noqa: N812
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .config_flow import CONFIG_VERSION
from .const import (
    ATTR_BATTERY_LAST_REPORTED,
    ATTR_BATTERY_LAST_REPORTED_DAYS,
    ATTR_BATTERY_LAST_REPORTED_LEVEL,
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_PREVIOUS_BATTERY_LEVEL,
    ATTR_REMOVE,
    ATTR_SOURCE_ENTITY_ID,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_ENABLE_REPLACED,
    CONF_HIDE_BATTERY,
    CONF_ROUND_BATTERY,
    CONF_SHOW_ALL_DEVICES,
    CONF_USER_LIBRARY,
    DATA,
    DATA_LIBRARY_UPDATER,
    DATA_STORE,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DOMAIN,
    DOMAIN_CONFIG,
    EVENT_BATTERY_NOT_REPORTED,
    EVENT_BATTERY_THRESHOLD,
    MIN_HA_VERSION,
    PLATFORMS,
    SERVICE_BATTERY_REPLACED,
    SERVICE_BATTERY_REPLACED_SCHEMA,
    SERVICE_CHECK_BATTERY_LAST_REPORTED,
    SERVICE_CHECK_BATTERY_LAST_REPORTED_SCHEMA,
    SERVICE_CHECK_BATTERY_LOW,
    SERVICE_DATA_DATE_TIME_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPORTED,
)
from .device import BatteryNotesDevice
from .discovery import DiscoveryManager
from .library_updater import (
    LibraryUpdater,
)
from .store import (
    async_get_registry,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            vol.Schema(
                {
                    vol.Optional(CONF_ENABLE_AUTODISCOVERY, default=True): cv.boolean,
                    vol.Optional(CONF_USER_LIBRARY, default=""): cv.string,
                    vol.Optional(CONF_SHOW_ALL_DEVICES, default=False): cv.boolean,
                    vol.Optional(CONF_ENABLE_REPLACED, default=True): cv.boolean,
                    vol.Optional(CONF_HIDE_BATTERY, default=False): cv.boolean,
                    vol.Optional(CONF_ROUND_BATTERY, default=False): cv.boolean,
                    vol.Optional(
                        CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
                        default=DEFAULT_BATTERY_LOW_THRESHOLD,
                    ): cv.positive_int,
                    vol.Optional(
                        CONF_BATTERY_INCREASE_THRESHOLD,
                        default=DEFAULT_BATTERY_INCREASE_THRESHOLD,
                    ): cv.positive_int,
                },
            ),
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


@dataclass
class BatteryNotesData:
    """Class for sharing data within the BatteryNotes integration."""

    devices: dict[str, BatteryNotesDevice] = field(default_factory=dict)
    platforms: dict = field(default_factory=dict)


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
        CONF_SHOW_ALL_DEVICES: False,
        CONF_ENABLE_REPLACED: True,
        CONF_HIDE_BATTERY: False,
        CONF_ROUND_BATTERY: False,
        CONF_DEFAULT_BATTERY_LOW_THRESHOLD: DEFAULT_BATTERY_LOW_THRESHOLD,
        CONF_BATTERY_INCREASE_THRESHOLD: DEFAULT_BATTERY_INCREASE_THRESHOLD,
    }

    hass.data[DOMAIN] = {
        DOMAIN_CONFIG: domain_config,
    }

    store = await async_get_registry(hass)
    hass.data[DOMAIN][DATA_STORE] = store

    hass.data[DOMAIN][DATA] = BatteryNotesData()

    library_updater = LibraryUpdater(hass)

    await library_updater.get_library_updates(dt_util.utcnow())

    hass.data[DOMAIN][DATA_LIBRARY_UPDATER] = library_updater

    if domain_config.get(CONF_ENABLE_AUTODISCOVERY):
        discovery_manager = DiscoveryManager(hass, config)
        await discovery_manager.start_discovery()
    else:
        _LOGGER.debug("Auto discovery disabled")

    # Register custom services
    register_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up a config entry."""

    device: BatteryNotesDevice = BatteryNotesDevice(hass, config_entry)

    if not await device.async_setup():
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    data: BatteryNotesData = hass.data[DOMAIN][DATA]

    device = data.devices.pop(config_entry.entry_id)
    await device.async_unload()

    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Device removed, tidy up store."""

    if "device_id" not in config_entry.data:
        return

    if config_entry.entry_id not in hass.data[DOMAIN][DATA].devices:
        return

    device: BatteryNotesDevice = hass.data[DOMAIN][DATA].devices[config_entry.entry_id]
    if not device:
        return

    data = {ATTR_REMOVE: True}

    device.coordinator.async_update_device_config(
        device_id=device.coordinator.device_id, data=data
    )

    _LOGGER.debug("Removed Device %s", device.coordinator.device_id)

    # Unhide the battery
    entity_registry = er.async_get(hass)
    if not device.wrapped_battery:
        return

    if not (
        wrapped_battery_entity_entry := entity_registry.async_get(
            device.wrapped_battery.entity_id
        )
    ):
        return

    if wrapped_battery_entity_entry.hidden_by == er.RegistryEntryHider.INTEGRATION:
        entity_registry.async_update_entity(
            device.wrapped_battery.entity_id, hidden_by=None
        )
        _LOGGER.debug(
            "Unhidden Original Battery for device%s", device.coordinator.device_id
        )


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old config."""
    new_version = CONFIG_VERSION

    if config_entry.version == 1:
        # Version 1 had a single config for qty & type, split them
        _LOGGER.debug("Migrating config entry from version %s", config_entry.version)

        matches: re.Match = re.search(
            r"^(\d+)(?=x)(?:x\s)(\w+$)|([\s\S]+)", config_entry.data[CONF_BATTERY_TYPE]
        )
        if matches:
            _qty = matches.group(1) if matches.group(1) is not None else "1"
            _type = (
                matches.group(2) if matches.group(2) is not None else matches.group(3)
            )
        else:
            _qty = 1
            _type = config_entry.data[CONF_BATTERY_TYPE]

        new_data = {**config_entry.data}
        new_data[CONF_BATTERY_TYPE] = _type
        new_data[CONF_BATTERY_QUANTITY] = _qty

        hass.config_entries.async_update_entry(
            config_entry, version=new_version, title=config_entry.title, data=new_data
        )

        _LOGGER.info(
            "Entry %s successfully migrated to version %s.",
            config_entry.entry_id,
            new_version,
        )

    return True


@callback
async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)


@callback
def register_services(hass: HomeAssistant):
    """Register services used by battery notes component."""

    async def handle_battery_replaced(call):
        """Handle the service call."""
        device_id = call.data.get(ATTR_DEVICE_ID, "")
        source_entity_id = call.data.get(ATTR_SOURCE_ENTITY_ID, "")
        datetime_replaced_entry = call.data.get(SERVICE_DATA_DATE_TIME_REPLACED)

        if datetime_replaced_entry:
            datetime_replaced = dt_util.as_utc(datetime_replaced_entry).replace(
                tzinfo=None
            )
        else:
            datetime_replaced = datetime.utcnow()

        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)

        if source_entity_id:
            source_entity_entry = entity_registry.async_get(source_entity_id)
            if not source_entity_entry:
                _LOGGER.error(
                    "Entity %s not found",
                    source_entity_id,
                )
                return

            # entity_id is the associated entity, now need to find the config entry for battery notes
            for config_entry in hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("source_entity_id") == source_entity_id:
                    config_entry_id = config_entry.entry_id

                    coordinator = (
                        hass.data[DOMAIN][DATA].devices[config_entry_id].coordinator
                    )

                    entry = {"battery_last_replaced": datetime_replaced}

                    coordinator.async_update_entity_config(
                        entity_id=source_entity_id, data=entry
                    )
                    await coordinator.async_request_refresh()

                    _LOGGER.debug(
                        "Entity %s battery replaced on %s",
                        source_entity_id,
                        str(datetime_replaced),
                    )

                    return

            _LOGGER.error("Entity %s not configured in Battery Notes", source_entity_id)

        else:
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                _LOGGER.error(
                    "Device %s not found",
                    device_id,
                )
                return

            for entry_id in device_entry.config_entries:
                if (
                    entry := hass.config_entries.async_get_entry(entry_id)
                ) and entry.domain == DOMAIN:
                    coordinator = (
                        hass.data[DOMAIN][DATA].devices[entry.entry_id].coordinator
                    )

                    device_entry = {"battery_last_replaced": datetime_replaced}

                    coordinator.async_update_device_config(
                        device_id=device_id, data=device_entry
                    )

                    await coordinator.async_request_refresh()

                    _LOGGER.debug(
                        "Device %s battery replaced on %s",
                        device_id,
                        str(datetime_replaced),
                    )

                    # Found and dealt with, exit
                    return

            _LOGGER.error(
                "Device %s not configured in Battery Notes",
                device_id,
            )

    async def handle_battery_last_reported(call):
        """Handle the service call."""
        days_last_reported = call.data.get(SERVICE_DATA_DAYS_LAST_REPORTED)

        device: BatteryNotesDevice
        for device in hass.data[DOMAIN][DATA].devices.values():
            if device.coordinator.last_reported:
                time_since_lastreported = (
                    datetime.fromisoformat(str(datetime.utcnow()) + "+00:00")
                    - device.coordinator.last_reported
                )

                if time_since_lastreported.days > days_last_reported:
                    hass.bus.async_fire(
                        EVENT_BATTERY_NOT_REPORTED,
                        {
                            ATTR_DEVICE_ID: device.coordinator.device_id or "",
                            ATTR_SOURCE_ENTITY_ID: device.coordinator.source_entity_id
                            or "",
                            ATTR_DEVICE_NAME: device.coordinator.device_name,
                            ATTR_BATTERY_TYPE_AND_QUANTITY: device.coordinator.battery_type_and_quantity,
                            ATTR_BATTERY_TYPE: device.coordinator.battery_type,
                            ATTR_BATTERY_QUANTITY: device.coordinator.battery_quantity,
                            ATTR_BATTERY_LAST_REPORTED: device.coordinator.last_reported,
                            ATTR_BATTERY_LAST_REPORTED_DAYS: time_since_lastreported.days,
                            ATTR_BATTERY_LAST_REPORTED_LEVEL: device.coordinator.last_reported_level,
                        },
                    )

                    _LOGGER.debug(
                        "Raised event device %s not reported since %s",
                        device.coordinator.device_id,
                        str(device.coordinator.last_reported),
                    )

    async def handle_battery_low(call):
        """Handle the service call."""

        device: BatteryNotesDevice
        for device in hass.data[DOMAIN][DATA].devices.values():
            if device.coordinator.battery_low is True:
                hass.bus.async_fire(
                    EVENT_BATTERY_THRESHOLD,
                    {
                        ATTR_DEVICE_ID: device.coordinator.device_id or "",
                        ATTR_DEVICE_NAME: device.coordinator.device_name,
                        ATTR_SOURCE_ENTITY_ID: device.coordinator.source_entity_id
                        or "",
                        ATTR_BATTERY_LOW: device.coordinator.battery_low,
                        ATTR_BATTERY_TYPE_AND_QUANTITY: device.coordinator.battery_type_and_quantity,
                        ATTR_BATTERY_TYPE: device.coordinator.battery_type,
                        ATTR_BATTERY_QUANTITY: device.coordinator.battery_quantity,
                        ATTR_BATTERY_LEVEL: device.coordinator.rounded_battery_level,
                        ATTR_PREVIOUS_BATTERY_LEVEL: device.coordinator.rounded_previous_battery_level,
                        ATTR_BATTERY_THRESHOLD_REMINDER: True,
                    },
                )

                _LOGGER.debug(
                    "Raised event device %s battery low",
                    device.coordinator.device_id,
                )

    hass.services.async_register(
        DOMAIN,
        SERVICE_BATTERY_REPLACED,
        handle_battery_replaced,
        schema=SERVICE_BATTERY_REPLACED_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LAST_REPORTED,
        handle_battery_last_reported,
        schema=SERVICE_CHECK_BATTERY_LAST_REPORTED_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LOW,
        handle_battery_low,
    )

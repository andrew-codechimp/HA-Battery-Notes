"""Battery Notes integration for Home Assistant.

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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util
from homeassistant.util.hass_dict import HassKey

from .config_flow import CONFIG_VERSION
from .const import (
    ATTR_REMOVE,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_ENABLE_REPLACED,
    CONF_HIDE_BATTERY,
    CONF_LIBRARY_URL,
    CONF_ROUND_BATTERY,
    CONF_SCHEMA_URL,
    CONF_SHOW_ALL_DEVICES,
    CONF_USER_LIBRARY,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DEFAULT_LIBRARY_URL,
    DEFAULT_SCHEMA_URL,
    DOMAIN,
    MIN_HA_VERSION,
    PLATFORMS,
)
from .coordinator import BatteryNotesCoordinator
from .discovery import DiscoveryManager
from .library_updater import LibraryUpdater
from .services import setup_services
from .store import (
    BatteryNotesStorage,
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
                    vol.Optional(
                        CONF_LIBRARY_URL,
                        default=DEFAULT_LIBRARY_URL,
                    ): cv.string,
                    vol.Optional(
                        CONF_SCHEMA_URL,
                        default=DEFAULT_SCHEMA_URL,
                    ): cv.string,
                },
            ),
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

@dataclass
class BatteryNotesDomainConfig:
    """Class for sharing config data within the BatteryNotes integration."""
    enable_autodiscovery: bool = True
    show_all_devices: bool = False
    enable_replaced: bool = True
    hide_battery: bool = False
    round_battery: bool = False
    default_battery_low_threshold: int = DEFAULT_BATTERY_LOW_THRESHOLD
    battery_increased_threshod: int = DEFAULT_BATTERY_INCREASE_THRESHOLD
    library_url: str = DEFAULT_LIBRARY_URL
    schema_url: str = DEFAULT_SCHEMA_URL
    library_updater: LibraryUpdater | None
    library_last_update: datetime | None = None
    user_library: str = ""
    coordinator: BatteryNotesCoordinator | None

type BatteryNotesConfigEntry = ConfigEntry[BatteryNotesData]

MY_KEY: HassKey["BatteryNotesDomainConfig"] = HassKey(DOMAIN)

@dataclass
class BatteryNotesData:
    """Class for sharing data within the BatteryNotes integration."""

    domain_config: BatteryNotesDomainConfig
    store: BatteryNotesStorage
    coordinator: BatteryNotesCoordinator


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

    library_updater = LibraryUpdater(hass)
    await library_updater.copy_schema()
    await library_updater.get_library_updates(dt_util.utcnow())

    domain_config = BatteryNotesDomainConfig(
        enable_autodiscovery=config.get(DOMAIN, {}).get(CONF_ENABLE_AUTODISCOVERY, True),
        show_all_devices=config.get(DOMAIN, {}).get(CONF_SHOW_ALL_DEVICES, False),
        enable_replaced=config.get(DOMAIN, {}).get(CONF_ENABLE_REPLACED, True),
        hide_battery=config.get(DOMAIN, {}).get(CONF_HIDE_BATTERY, False),
        round_battery=config.get(DOMAIN, {}).get(CONF_ROUND_BATTERY, False),
        default_battery_low_threshold=config.get(DOMAIN, {}).get(
            CONF_DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
        ),
        battery_increased_threshod=config.get(DOMAIN, {}).get(
            CONF_BATTERY_INCREASE_THRESHOLD, DEFAULT_BATTERY_INCREASE_THRESHOLD
        ),
        library_url=config.get(DOMAIN, {}).get(CONF_LIBRARY_URL, DEFAULT_LIBRARY_URL),
        schema_url=config.get(DOMAIN, {}).get(CONF_SCHEMA_URL, DEFAULT_SCHEMA_URL),
        library_updater=library_updater,
        user_library=config.get(DOMAIN, {}).get(CONF_USER_LIBRARY, ""),
    )

    hass.data[MY_KEY] = domain_config

    if domain_config.enable_autodiscovery:
        discovery_manager = DiscoveryManager(hass, domain_config)
        await discovery_manager.start_discovery()
    else:
        _LOGGER.debug("Auto discovery disabled")

    # Register custom services
    setup_services(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: BatteryNotesConfigEntry) -> bool:
    """Set up a config entry."""

    config_entry.runtime_data.domain_config = hass.data[MY_KEY]
    config_entry.runtime_data.store = await async_get_registry(hass, config_entry)
    config_entry.runtime_data.coordinator = BatteryNotesCoordinator(hass, config_entry)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: BatteryNotesConfigEntry) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, config_entry: BatteryNotesConfigEntry) -> None:
    """Device removed, tidy up store."""

    # Remove any issues raised
    ir.async_delete_issue(hass, DOMAIN, f"missing_device_{config_entry.entry_id}")

    config_entry.runtime_data.coordinator.async_update_device_config

    if not config_entry.runtime_data.coordinator.device_id:
        return

    data = {ATTR_REMOVE: True}

    config_entry.runtime_data.coordinator.async_update_device_config(
        device_id=config_entry.runtime_data.coordinator.device_id, data=data
    )

    _LOGGER.debug("Removed Device %s", config_entry.runtime_data.coordinator.device_id)

    # Unhide the battery
    entity_registry = er.async_get(hass)
    if not config_entry.runtime_data.coordinator.wrapped_battery:
        return

    if not (
        wrapped_battery_entity_entry := entity_registry.async_get(
            config_entry.runtime_data.coordinator.wrapped_battery.entity_id
        )
    ):
        return

    if wrapped_battery_entity_entry.hidden_by == er.RegistryEntryHider.INTEGRATION:
        entity_registry.async_update_entity(
            config_entry.runtime_data.wrapped_battery.entity_id, hidden_by=None
        )
        _LOGGER.debug(
            "Unhidden Original Battery for device%s", config_entry.runtime_data.coordinator.device_id
        )


async def async_migrate_entry(hass: HomeAssistant, config_entry: BatteryNotesConfigEntry):
    """Migrate old config."""
    new_version = CONFIG_VERSION

    if config_entry.version == 1:
        # Version 1 had a single config for qty & type, split them
        _LOGGER.debug("Migrating config entry from version %s", config_entry.version)

        matches = re.search(
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


async def update_listener(
    hass: HomeAssistant, config_entry: BatteryNotesConfigEntry
) -> None:
    """Update the device and related entities.

    Triggered when the device is renamed on the frontend.
    """

    await hass.config_entries.async_reload(config_entry.entry_id)


@callback
async def async_update_options(hass: HomeAssistant, entry: BatteryNotesConfigEntry) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)

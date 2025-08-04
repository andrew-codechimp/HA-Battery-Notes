"""Battery Notes integration for Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-battery-notes
"""

from __future__ import annotations

import logging
import re
from typing import Any, Final

import voluptuous as vol
from awesomeversion.awesomeversion import AwesomeVersion
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_SOURCE
from homeassistant.const import __version__ as HA_VERSION  # noqa: N812
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.typing import ConfigType

from .config_flow import CONFIG_VERSION
from .const import (
    CONF_ADVANCED_SETTINGS,
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
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DOMAIN,
    MIN_HA_VERSION,
    PLATFORMS,
)
from .const import (
    NAME as INTEGRATION_NAME,
)
from .coordinator import (
    MY_KEY,
    BatteryNotesConfigEntry,
    BatteryNotesCoordinator,
    BatteryNotesData,
    BatteryNotesDomainConfig,
)
from .discovery import DiscoveryManager
from .library_updater import LibraryUpdater
from .services import async_setup_services
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

_migrate_base_entry: ConfigEntry = None
_yaml_domain_config: list[dict[str, Any]] | None = None

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Integration setup."""

    if AwesomeVersion(HA_VERSION) < AwesomeVersion(MIN_HA_VERSION):  # pragma: no cover
        msg = (
            "This integration requires at least Home Assistant version "
            f" {MIN_HA_VERSION}, you are running version {HA_VERSION}."
            " Please upgrade Home Assistant to continue using this integration."
        )
        _LOGGER.critical(msg)
        return False

    store = await async_get_registry(hass)

    domain_config = BatteryNotesDomainConfig(
        user_library=config.get(DOMAIN, {}).get(CONF_USER_LIBRARY, ""),
        store=store,
    )

    yaml_domain_config: list[dict[str, Any]] | None = config.get(DOMAIN)
    if yaml_domain_config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={CONF_SOURCE: SOURCE_IMPORT},
                data={
                    CONF_SHOW_ALL_DEVICES: yaml_domain_config.get(CONF_SHOW_ALL_DEVICES, False),
                    CONF_HIDE_BATTERY: yaml_domain_config.get(CONF_HIDE_BATTERY, False),
                    CONF_ROUND_BATTERY: yaml_domain_config.get(CONF_ROUND_BATTERY, False),
                    CONF_DEFAULT_BATTERY_LOW_THRESHOLD: yaml_domain_config.get(
                        CONF_DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
                    ),
                    CONF_BATTERY_INCREASE_THRESHOLD: yaml_domain_config.get(
                        CONF_BATTERY_INCREASE_THRESHOLD, DEFAULT_BATTERY_INCREASE_THRESHOLD
                    ),
                    CONF_ADVANCED_SETTINGS: {
                        CONF_ENABLE_AUTODISCOVERY: yaml_domain_config.get(CONF_ENABLE_AUTODISCOVERY, True),
                        CONF_ENABLE_REPLACED: yaml_domain_config.get(CONF_ENABLE_REPLACED, True),
                        CONF_USER_LIBRARY: yaml_domain_config.get(CONF_USER_LIBRARY, ""),
                    },
                }
            )
        )

    hass.data[MY_KEY] = domain_config

    library_updater = LibraryUpdater(hass)
    await library_updater.copy_schema()
    await library_updater.get_library_updates(startup=True)

    # Register custom services
    async_setup_services(hass)

    return True


async def async_setup_entry(
    hass: HomeAssistant, config_entry: BatteryNotesConfigEntry
) -> bool:
    """Set up a config entry."""

    domain_config = hass.data[MY_KEY]
    assert domain_config.store

    domain_config.show_all_devices = config_entry.options[CONF_SHOW_ALL_DEVICES]
    domain_config.hide_battery = config_entry.options[CONF_HIDE_BATTERY]
    domain_config.round_battery = config_entry.options[CONF_ROUND_BATTERY]
    domain_config.default_battery_low_threshold = config_entry.options[CONF_DEFAULT_BATTERY_LOW_THRESHOLD]
    domain_config.battery_increased_threshod = config_entry.options[CONF_BATTERY_INCREASE_THRESHOLD]

    domain_config.enable_autodiscovery = config_entry.options[CONF_ADVANCED_SETTINGS][CONF_ENABLE_AUTODISCOVERY]
    domain_config.enable_replaced = config_entry.options[CONF_ADVANCED_SETTINGS][CONF_ENABLE_REPLACED]
    domain_config.user_library = config_entry.options[CONF_ADVANCED_SETTINGS][CONF_USER_LIBRARY]

    config_entry.runtime_data = BatteryNotesData(
        domain_config=domain_config,
        store=domain_config.store,
    )

    # TODO: Get this working
    config_entry.runtime_data.subentry_coordinators = {}
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == "battery_note":
            coordinator = BatteryNotesCoordinator(hass, config_entry, subentry)
            config_entry.runtime_data.subentry_coordinators[subentry.subentry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(config_entry.add_update_listener(update_listener))

    if domain_config.enable_autodiscovery:
        discovery_manager = DiscoveryManager(hass, domain_config)
        await discovery_manager.start_discovery()
    else:
        _LOGGER.debug("Auto discovery disabled")

    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: BatteryNotesConfigEntry
) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_remove_entry(
    hass: HomeAssistant, config_entry: BatteryNotesConfigEntry
) -> None:
    """Device removed, tidy up store."""

    # Remove any issues raised
    ir.async_delete_issue(hass, DOMAIN, f"missing_device_{config_entry.entry_id}")

    store = await async_get_registry(hass)
    coordinator = BatteryNotesCoordinator(hass, config_entry)

    if coordinator.source_entity_id:
        store.async_delete_entity(coordinator.source_entity_id)
    else:
        if coordinator.device_id:
            store.async_delete_device(coordinator.device_id)

    _LOGGER.debug("Removed battery note %s", config_entry.entry_id)

    # Unhide the battery
    entity_registry = er.async_get(hass)
    if not coordinator.wrapped_battery:
        return

    if not (
        wrapped_battery_entity_entry := entity_registry.async_get(
            coordinator.wrapped_battery.entity_id
        )
    ):
        return

    if wrapped_battery_entity_entry.hidden_by == er.RegistryEntryHider.INTEGRATION:
        entity_registry.async_update_entity(
            coordinator.wrapped_battery.entity_id, hidden_by=None
        )
        _LOGGER.debug("Unhidden Original Battery for device%s", coordinator.device_id)


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: BatteryNotesConfigEntry
):
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

    if config_entry.version < 3:
        # Get the current config entries, see if one is at V3 and hold onto it as the base
        if not _migrate_base_entry:
            _LOGGER.debug("No base entry, looking for existing V3 entries")

            existing_entries = hass.config_entries.async_entries(DOMAIN)
            for entry in existing_entries:
                if entry.version == 3 and entry.unique_id == DOMAIN:
                    # We have a V3 entry, so we can use this as the base
                    _LOGGER.debug(
                        "Found existing V3 config entry %s, using it as the base for migration",
                        entry.entry_id,
                    )
                    _migrate_base_entry = entry
                    break
        # If no V3 then create one and hold onto it as the base
        if not _migrate_base_entry:
            _LOGGER.debug(
                "No existing V3 config entry found, creating a new one for migration"
            )

            if _yaml_domain_config:
                options={
                    CONF_SHOW_ALL_DEVICES: _yaml_domain_config.get(CONF_SHOW_ALL_DEVICES, False),
                    CONF_HIDE_BATTERY: _yaml_domain_config.get(CONF_HIDE_BATTERY, False),
                    CONF_ROUND_BATTERY: _yaml_domain_config.get(CONF_ROUND_BATTERY, False),
                    CONF_DEFAULT_BATTERY_LOW_THRESHOLD: _yaml_domain_config.get(
                        CONF_DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
                    ),
                    CONF_BATTERY_INCREASE_THRESHOLD: _yaml_domain_config.get(
                        CONF_BATTERY_INCREASE_THRESHOLD, DEFAULT_BATTERY_INCREASE_THRESHOLD
                    ),
                    CONF_ADVANCED_SETTINGS: {
                        CONF_ENABLE_AUTODISCOVERY: _yaml_domain_config.get(CONF_ENABLE_AUTODISCOVERY, True),
                        CONF_ENABLE_REPLACED: _yaml_domain_config.get(CONF_ENABLE_REPLACED, True),
                        CONF_USER_LIBRARY: _yaml_domain_config.get(CONF_USER_LIBRARY, ""),
                    },
                }
            else:
                options={
                    CONF_SHOW_ALL_DEVICES: False,
                    CONF_HIDE_BATTERY: False,
                    CONF_ROUND_BATTERY: False,
                    CONF_DEFAULT_BATTERY_LOW_THRESHOLD: DEFAULT_BATTERY_LOW_THRESHOLD,
                    CONF_BATTERY_INCREASE_THRESHOLD: DEFAULT_BATTERY_INCREASE_THRESHOLD,
                    CONF_ADVANCED_SETTINGS: {
                        CONF_ENABLE_AUTODISCOVERY: True,
                        CONF_ENABLE_REPLACED: True,
                        CONF_USER_LIBRARY: "",
                    },
                }

            _migrate_base_entry = ConfigEntry(
                domain=DOMAIN,
                title=INTEGRATION_NAME,
                version=3,
                unique_id=DOMAIN,
                optons=options,
                )
            hass.config_entries.async_add(_migrate_base_entry)

        assert _migrate_base_entry is not None, "Base entry should not be None"

        # TODO: Change this config entry into a sub entry, add it to the base entry

        _LOGGER.debug(
            "Migrating config entry %s from version %s to version %s",
            config_entry.entry_id,
            config_entry.version,
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
async def async_update_options(
    hass: HomeAssistant, entry: BatteryNotesConfigEntry
) -> None:
    """Update options."""
    await hass.config_entries.async_reload(entry.entry_id)

"""Battery Notes integration for Home Assistant.

For more details about this integration, please refer to
https://github.com/andrew-codechimp/ha-battery-notes
"""

from __future__ import annotations

import logging
import re

import voluptuous as vol
from awesomeversion.awesomeversion import AwesomeVersion
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.const import __version__ as HA_VERSION  # noqa: N812
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import helper_integration
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.device import (
    async_entity_id_to_device_id,
)
from homeassistant.helpers.issue_registry import IssueSeverity, async_create_issue
from homeassistant.helpers.typing import ConfigType

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
    ISSUE_DEPRECATED_YAML,
    MIN_HA_VERSION,
    PLATFORMS,
    SUBENTRY_BATTERY_NOTE,
)
from .const import NAME as INTEGRATION_NAME
from .coordinator import (
    MY_KEY,
    BatteryNotesConfigEntry,
    BatteryNotesData,
    BatteryNotesDomainConfig,
    BatteryNotesSubentryCoordinator,
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

    await async_migrate_integration(hass, config)

    store = await async_get_registry(hass)

    domain_config = BatteryNotesDomainConfig(
        store=store,
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
        loaded_subentries=config_entry.subentries.copy(),
    )

    config_entry.runtime_data.subentry_coordinators = {}
    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == SUBENTRY_BATTERY_NOTE:

            coordinator = BatteryNotesSubentryCoordinator(hass, config_entry, subentry)
            config_entry.runtime_data.subentry_coordinators[subentry.subentry_id] = coordinator

            assert subentry.unique_id

            # Create a device, only needed if we want entities that are not added to the source device
            # device_registry = dr.async_get(hass)
            # device_registry.async_get_or_create(
            #     config_entry_id=config_entry.entry_id,
            #     config_subentry_id= subentry.subentry_id,
            #     identifiers={(DOMAIN, coordinator.unique_id)},
            #     entry_type=DeviceEntryType.SERVICE,
            #     manufacturer=MANUFACTURER,
            #     name=subentry.title
            # )


    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    config_entry.async_on_unload(config_entry.add_update_listener(_async_update_listener))

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
    """Battery Notes integration removed."""

    for subentry in config_entry.subentries.values():
        if subentry.subentry_id not in config_entry.subentries:
            await _async_remove_subentry(hass, config_entry, subentry, remove_store_entries=False)

async def async_migrate_integration(hass: HomeAssistant, config: ConfigType) -> None:
    """Migrate integration entry structure."""

    migrate_base_entry: ConfigEntry | None = None

    yaml_domain_config = config.get(DOMAIN)
    if yaml_domain_config is not None:
        async_create_issue(
            hass,
            DOMAIN,
            ISSUE_DEPRECATED_YAML,
            is_fixable=False,
            issue_domain=DOMAIN,
            severity=IssueSeverity.WARNING,
            translation_key=ISSUE_DEPRECATED_YAML,
            translation_placeholders={
                "domain": DOMAIN,
                "integration_title": INTEGRATION_NAME,
            },
        )

    entries = hass.config_entries.async_entries(DOMAIN)
    if not any(entry.version < 3 for entry in entries):
        return

    for entry in entries:
        if entry.version == 3 and entry.unique_id == DOMAIN:
            # We have a V3 entry, so we can use this as the base
            migrate_base_entry = entry
            break

    for entry in entries:
        if entry.version >= 3:
            continue

        subentry = ConfigSubentry(
            data=entry.data,
            subentry_type=SUBENTRY_BATTERY_NOTE,
            title=entry.title,
            unique_id=entry.unique_id,
        )

        if not migrate_base_entry:
            if yaml_domain_config:
                options={
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

            hass.config_entries.async_update_entry(
                entry,
                version=3,
                title=INTEGRATION_NAME,
                data={},
                options=options,
                unique_id=DOMAIN,
            )

            migrate_base_entry = entry

        hass.config_entries.async_add_subentry(migrate_base_entry, subentry)

        source_device_id = subentry.data.get(CONF_DEVICE_ID, None)
        source_entity_id = subentry.data.get("source_entity_id", None)
        if source_entity_id:
            source_device_id = async_entity_id_to_device_id(
                hass, source_entity_id
            )

        if source_device_id:
            helper_integration.async_remove_helper_config_entry_from_source_device(hass=hass, helper_config_entry_id=entry.entry_id, source_device_id=source_device_id)

        # Remove the old config entry
        if entry.entry_id != migrate_base_entry.entry_id:
            await hass.config_entries.async_remove(entry.entry_id)

        _LOGGER.info(
            "Entry %s successfully migrated to subentry of %s.",
            entry.entry_id,
            migrate_base_entry.entry_id,
        )


async def async_migrate_entry(
    hass: HomeAssistant, config_entry: BatteryNotesConfigEntry
):
    """Migrate old config."""

    if config_entry.version == 1:
        # Version 1 had a single config for qty & type, split them
        _LOGGER.debug("Migrating config entry from version %s", config_entry.version)

        matches = re.search(
            r"^(\d+)(?=x)(?:x\s)(\w+$)|([\s\S]+)", config_entry.data[CONF_BATTERY_TYPE]
        )
        if matches:
            qty = matches.group(1) if matches.group(1) is not None else "1"
            type = (
                matches.group(2) if matches.group(2) is not None else matches.group(3)
            )
        else:
            qty = 1
            type = config_entry.data[CONF_BATTERY_TYPE]

        new_data = {**config_entry.data}
        new_data[CONF_BATTERY_TYPE] = type
        new_data[CONF_BATTERY_QUANTITY] = qty

        hass.config_entries.async_update_entry(
            config_entry, version=2, title=config_entry.title, data=new_data
        )

        _LOGGER.info(
            "Entry %s successfully migrated to version %s.",
            config_entry.entry_id,
            2,
        )

    return True


async def _async_update_listener(
    hass: HomeAssistant, config_entry: BatteryNotesConfigEntry
) -> None:
    """Update the device and related entities.

    Triggered when the device is renamed on the frontend, or when sub entries are updated.

    Look at sub entries and remove any that are no longer present.
    """

    for subentry in config_entry.runtime_data.loaded_subentries.values():
        if subentry.subentry_id not in config_entry.subentries:
            await _async_remove_subentry(hass, config_entry, subentry, remove_store_entries=False)

    # Update the config entry with the new sub entries
    config_entry.runtime_data.loaded_subentries = config_entry.subentries.copy()

    await hass.config_entries.async_reload(config_entry.entry_id)


async def _async_remove_subentry(
    hass: HomeAssistant,
    config_entry: BatteryNotesConfigEntry,
    subentry: ConfigSubentry,
    remove_store_entries: bool,
) -> None:
    """Remove a sub entry."""
    _LOGGER.debug("Removing sub entry %s from config entry %s", subentry.subentry_id, config_entry.entry_id)

    assert config_entry.runtime_data.subentry_coordinators
    coordinator = config_entry.runtime_data.subentry_coordinators.get(subentry.subentry_id)
    assert coordinator

    # Remove any issues raised
    ir.async_delete_issue(hass, DOMAIN, f"missing_device_{subentry.subentry_id}")

    # Remove store entries
    if remove_store_entries:
        store = coordinator.config_entry.runtime_data.store

        if coordinator.source_entity_id:
            store.async_delete_entity(coordinator.source_entity_id)
        else:
            if coordinator.device_id:
                store.async_delete_device(coordinator.device_id)

    # Unhide the battery
    if coordinator.wrapped_battery:
        entity_registry = er.async_get(hass)
        if (
            wrapped_battery_entity_entry := entity_registry.async_get(
                coordinator.wrapped_battery.entity_id
            )
        ):
            if wrapped_battery_entity_entry.hidden_by == er.RegistryEntryHider.INTEGRATION:
                entity_registry.async_update_entity(
                    coordinator.wrapped_battery.entity_id, hidden_by=None
                )
                _LOGGER.debug("Unhidden Original Battery for device%s", coordinator.device_id)

    config_entry.runtime_data.subentry_coordinators.pop(subentry.subentry_id)

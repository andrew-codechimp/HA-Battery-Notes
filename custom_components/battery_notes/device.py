"""Battery Notes device, contains device level details."""

import logging
from datetime import datetime
from typing import cast

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    PERCENTAGE,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_registry import RegistryEntry

from .const import (
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_SOURCE_ENTITY_ID,
    DATA,
    DATA_STORE,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DOMAIN,
    DOMAIN_CONFIG,
    PLATFORMS,
)
from .coordinator import BatteryNotesCoordinator
from .store import BatteryNotesStorage

_LOGGER = logging.getLogger(__name__)


class BatteryNotesDevice:
    """Manages a Battery Note device."""

    config: ConfigEntry
    store: BatteryNotesStorage
    coordinator: BatteryNotesCoordinator
    wrapped_battery: RegistryEntry | None = None
    device_name: str | None = None

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the device."""
        self.hass = hass
        self.config = config
        self.reset_jobs: list[CALLBACK_TYPE] = []

    @property
    def fake_device(self) -> bool:
        """Return if an actual device registry entry."""
        if self.config.data.get(CONF_SOURCE_ENTITY_ID, None):
            if self.config.data.get(CONF_DEVICE_ID, None) is None:
                return True
        return False

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self.device_name or self.config.title

    @property
    def unique_id(self) -> str | None:
        """Return the unique id of the device."""
        return self.config.unique_id

    @staticmethod
    async def async_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Update the device and related entities.

        Triggered when the device is renamed on the frontend.
        """
        await hass.config_entries.async_reload(entry.entry_id)

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        config = self.config

        device_id = config.data.get(CONF_DEVICE_ID, None)
        source_entity_id = config.data.get(CONF_SOURCE_ENTITY_ID, None)

        device_registry = dr.async_get(self.hass)
        entity_registry = er.async_get(self.hass)

        if source_entity_id:
            entity = entity_registry.async_get(source_entity_id)

            if not entity:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"missing_device_{self.config.entry_id}",
                    data={
                        "entry_id": self.config.entry_id,
                        "device_id": device_id,
                        "source_entity_id": source_entity_id,
                    },
                    is_fixable=True,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="missing_device",
                    translation_placeholders={
                            "name": config.title,
                        },
                )

                _LOGGER.warning(
                    "%s is orphaned, unable to find entity %s",
                    self.config.entry_id,
                    source_entity_id,
                )
                return False

            device_class = entity.device_class or entity.original_device_class
            if (
                device_class == SensorDeviceClass.BATTERY
                and entity.unit_of_measurement == PERCENTAGE
            ):
                self.wrapped_battery = entity
            else:
                _LOGGER.debug(
                    "%s is not a battery entity device_class: %s unit_of_measurement: %s",
                    source_entity_id,
                    device_class,
                    entity.unit_of_measurement,
                )

            if entity.device_id:
                device_entry = device_registry.async_get(entity.device_id)
                if device_entry:
                    self.device_name = (
                        device_entry.name_by_user
                        or device_entry.name
                        or self.config.title
                    )
                else:
                    self.device_name = self.config.title
            else:
                self.device_name = self.config.title
        else:
            for entity in entity_registry.entities.values():
                if not entity.device_id or entity.device_id != device_id:
                    continue
                if not entity.domain or entity.domain != SENSOR_DOMAIN:
                    continue
                if not entity.platform or entity.platform == DOMAIN:
                    continue

                if entity.disabled:
                    continue

                device_class = entity.device_class or entity.original_device_class
                if device_class != SensorDeviceClass.BATTERY:
                    continue

                if entity.unit_of_measurement != PERCENTAGE:
                    continue

                self.wrapped_battery = entity_registry.async_get(entity.entity_id)
                break

            device_entry = device_registry.async_get(device_id)
            if device_entry:
                self.device_name = (
                    device_entry.name_by_user or device_entry.name or self.config.title
                )
            else:
                self.device_name = self.config.title

                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"missing_device_{self.config.entry_id}",
                    data={
                        "entry_id": self.config.entry_id,
                        "device_id": device_id,
                        "source_entity_id": source_entity_id,
                    },
                    is_fixable=True,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="missing_device",
                    translation_placeholders={
                            "name": config.title,
                        },
                )

                _LOGGER.warning(
                    "%s is orphaned, unable to find device %s",
                    self.config.entry_id,
                    device_id,
                )
                return False

        self.store = self.hass.data[DOMAIN][DATA_STORE]
        self.coordinator = BatteryNotesCoordinator(
            self.hass, self.store, self.wrapped_battery
        )

        self.coordinator.device_id = device_id
        self.coordinator.source_entity_id = source_entity_id
        self.coordinator.device_name = self.device_name
        self.coordinator.battery_type = cast(str, config.data.get(CONF_BATTERY_TYPE))
        try:
            self.coordinator.battery_quantity = cast(int,
                config.data.get(CONF_BATTERY_QUANTITY)
            )
        except ValueError:
            self.coordinator.battery_quantity = 1

        self.coordinator.battery_low_threshold = int(
            config.data.get(CONF_BATTERY_LOW_THRESHOLD, 0)
        )

        if self.coordinator.battery_low_threshold == 0:
            domain_config: dict = self.hass.data[DOMAIN][DOMAIN_CONFIG]
            self.coordinator.battery_low_threshold = domain_config.get(
                CONF_DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
            )

        self.coordinator.battery_low_template = config.data.get(
            CONF_BATTERY_LOW_TEMPLATE
        )

        if self.wrapped_battery:
            _LOGGER.debug(
                "%s low threshold set at %d",
                self.wrapped_battery.entity_id,
                self.coordinator.battery_low_threshold,
            )

        # If there is not a last replaced, set to device created date if not epoch
        if not self.coordinator.last_replaced:
            last_replaced = None
            if entity.device_id:
                device_entry = device_registry.async_get(entity.device_id)

                if device_entry and device_entry.created_at.year > 1970:
                    last_replaced = device_entry.created_at.strftime(
                        "%Y-%m-%dT%H:%M:%S:%f"
                    )
            else:
                entity = entity_registry.async_get(source_entity_id)
                if entity and entity.created_at.year > 1970:
                    last_replaced = entity.created_at.strftime("%Y-%m-%dT%H:%M:%S:%f")

            _LOGGER.debug(
                "Defaulting %s battery last replaced to %s",
                source_entity_id or device_id,
                last_replaced,
            )

            self.coordinator.last_replaced = datetime.fromisoformat(last_replaced) if last_replaced else None

        # If there is not a last_reported set to now
        if not self.coordinator.last_reported:
            last_reported = datetime.utcnow()
            _LOGGER.debug(
                "Defaulting %s battery last reported to %s",
                source_entity_id or device_id,
                last_reported,
            )
            self.coordinator.last_reported = last_reported

        self.hass.data[DOMAIN][DATA].devices[config.entry_id] = self
        self.reset_jobs.append(config.add_update_listener(self.async_update))

        # Forward entry setup to related domains.
        await self.hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

        return True

    async def async_unload(self) -> bool:
        """Unload the device and related entities."""

        while self.reset_jobs:
            self.reset_jobs.pop()()

        return True

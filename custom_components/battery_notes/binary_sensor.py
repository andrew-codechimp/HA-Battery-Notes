"""Binary Sensor platform for battery_notes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
    async_track_entity_registry_updated_event,
)
from homeassistant.helpers.typing import EventType
from homeassistant.helpers.reload import async_setup_reload_service

from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICE_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from . import PLATFORMS

from .const import (
    DOMAIN,
    DOMAIN_CONFIG,
    DATA,
    CONF_ENABLE_REPLACED,
)

from .device import BatteryNotesDevice
from .coordinator import BatteryNotesCoordinator

from .entity import (
    BatteryNotesEntityDescription,
)


@dataclass
class BatteryNotesBinarySensorEntityDescription(
    BatteryNotesEntityDescription,
    BinarySensorEntityDescription,
):
    """Describes Battery Notes button entity."""

    unique_id_suffix: str


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {vol.Optional(CONF_NAME): cv.string, vol.Required(CONF_DEVICE_ID): cv.string}
)


@callback
def async_add_to_device(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Add our config entry to the device."""
    device_registry = dr.async_get(hass)

    device_id = entry.data.get(CONF_DEVICE_ID)
    device_registry.async_update_device(device_id, add_config_entry_id=entry.entry_id)

    return device_id


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    device_id = config_entry.data.get(CONF_DEVICE_ID)

    async def async_registry_updated(event: Event) -> None:
        """Handle entity registry update."""
        data = event.data
        if data["action"] == "remove":
            await hass.config_entries.async_remove(config_entry.entry_id)

        if data["action"] != "update":
            return

        if "entity_id" in data["changes"]:
            # Entity_id changed, reload the config entry
            await hass.config_entries.async_reload(config_entry.entry_id)

        if device_id and "device_id" in data["changes"]:
            # If the tracked battery note is no longer in the device, remove our config entry
            # from the device
            if (
                not (entity_entry := entity_registry.async_get(data[CONF_ENTITY_ID]))
                or not device_registry.async_get(device_id)
                or entity_entry.device_id == device_id
            ):
                # No need to do any cleanup
                return

            device_registry.async_update_device(
                device_id, remove_config_entry_id=config_entry.entry_id
            )

    coordinator = hass.data[DOMAIN][DATA].devices[config_entry.entry_id].coordinator

    config_entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, config_entry.entry_id, async_registry_updated
        )
    )

    device_id = async_add_to_device(hass, config_entry)

    enable_replaced = True
    if DOMAIN_CONFIG in hass.data[DOMAIN]:
        domain_config: dict = hass.data[DOMAIN][DOMAIN_CONFIG]
        enable_replaced = domain_config.get(CONF_ENABLE_REPLACED, True)

    description = BatteryNotesBinarySensorEntityDescription(
        unique_id_suffix="_battery_low",
        key="battery_low",
        translation_key="battery_low",
        icon="mdi:battery-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enable_replaced,
    )

    device = hass.data[DOMAIN][DATA].devices[config_entry.entry_id]

    if device.wrapped_battery is not None:
        async_add_entities(
            [
                BatteryNotesBatteryLowSensor(
                    hass,
                    coordinator,
                    description,
                    f"{config_entry.entry_id}{description.unique_id_suffix}",
                    device,
                )
            ]
        )


async def async_setup_platform(
    hass: HomeAssistant,
) -> None:
    """Set up the battery note sensor."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)


class BatteryNotesBatteryLowSensor(BinarySensorEntity):
    """Represents a low battery threshold binary sensor."""

    _attr_should_poll = False
    _battery_entity_id = None

    entity_description: BatteryNotesBinarySensorEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesBinarySensorEntityDescription,
        unique_id: str,
        device: BatteryNotesDevice,
    ) -> None:
        """Create a low battery binary sensor."""
        device_registry = dr.async_get(hass)

        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_has_entity_name = True

        if coordinator.device_id and (
            device_entry := device_registry.async_get(coordinator.device_id)
        ):
            self._attr_device_info = DeviceInfo(
                connections=device_entry.connections,
                identifiers=device_entry.identifiers,
            )

            self.entity_id = f"binary_sensor.{device.name}_{description.key}"

        self._battery_entity_id = (
            device.wrapped_battery.entity_id if device.wrapped_battery else None
        )

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._attr_unique_id},
            )

    @callback
    def async_state_changed_listener(
        self, event: EventType[EventStateChangedData] | None = None
    ) -> None:
        """Handle child updates."""
        updated = False

        if not self._battery_entity_id:
            return

        if (
            wrapped_battery_state := self.hass.states.get(self._battery_entity_id)
        ) is None or wrapped_battery_state.state == STATE_UNAVAILABLE:
            self._attr_available = False
            return

        self.coordinator.set_battery_low(bool(int(wrapped_battery_state.state) < 100))

        self._attr_is_on = self.coordinator.battery_low

        self._attr_available = True

        updated = True

        if updated:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        @callback
        def _async_state_changed_listener(
            event: EventType[EventStateChangedData] | None = None,
        ) -> None:
            """Handle child updates."""
            self.async_state_changed_listener(event)

        if self._battery_entity_id:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass, [self._battery_entity_id], _async_state_changed_listener
                )
            )

        # Call once on adding
        _async_state_changed_listener()

        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None and self._battery_entity_id:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._battery_entity_id},
            )

        self.coordinator.async_config_entry_first_refresh()

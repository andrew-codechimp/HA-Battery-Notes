"""Binary Sensor platform for battery_notes."""
from __future__ import annotations

from dataclasses import dataclass

import logging
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
    BinarySensorDeviceClass,
)

from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
)
from homeassistant.helpers.reload import async_setup_reload_service

from homeassistant.components.event import (
    EventEntity,
)

from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICE_ID,
)

from . import PLATFORMS

from .const import (
    DOMAIN,
    DATA,
    EVENT_BATTERY_THRESHOLD,
    ATTR_BATTERY_LOW_THRESHOLD,
)

from .device import BatteryNotesDevice
from .coordinator import BatteryNotesCoordinator

from .entity import (
    BatteryNotesEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


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

    description = BatteryNotesBinarySensorEntityDescription(
        unique_id_suffix="_battery_low",
        key="_battery_plus_low",
        translation_key="battery_low",
        icon="mdi:battery-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.BATTERY,
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


class BatteryNotesBatteryLowSensor(BinarySensorEntity, EventEntity):
    """Represents a low battery threshold binary sensor."""

    _attr_should_poll = False
    device_name = None
    _previous_battery_low = None
    _previous_battery_level = None
    _previous_state_last_changed = None
    device: BatteryNotesDevice

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
        self._attr_event_types = [EVENT_BATTERY_THRESHOLD]

        device_registry = dr.async_get(hass)

        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_has_entity_name = True
        self.device = device

        if coordinator.device_id and (
            device_entry := device_registry.async_get(coordinator.device_id)
        ):
            self._attr_device_info = DeviceInfo(
                connections=device_entry.connections,
                identifiers=device_entry.identifiers,
            )

            self.entity_id = f"binary_sensor.{device.name.lower()}_{description.key}"
            self.device_name = device.name

    @callback
    async def _async_handle_event(self, event) -> None:
        if event.event_type == EVENT_BATTERY_THRESHOLD:
            self._attr_is_on = self.coordinator.battery_low

            self._attr_available = True

            self.async_write_ha_state()

            _LOGGER.debug(
                "%s battery_low changed: %s", self.coordinator.wrapped_battery.entity_id, self.coordinator.battery_low
            )

            await self.coordinator.async_request_refresh()

            self._trigger_event(event.event_type, event.data)

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        self.hass.bus.async_listen(EVENT_BATTERY_THRESHOLD, self._async_handle_event)

        self._attr_is_on = self.coordinator.battery_low
        self._attr_available = True
        self.async_write_ha_state()

        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None and self.coordinator.wrapped_battery.entity_id:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self.coordinator.wrapped_battery.entity_id},
            )

        await self.coordinator.async_config_entry_first_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes of battery low."""

        attrs = {
            ATTR_BATTERY_LOW_THRESHOLD: self.coordinator.battery_low_threshold,
        }

        super_attrs = super().extra_state_attributes
        if super_attrs:
            attrs.update(super_attrs)
        return attrs

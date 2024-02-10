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
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
)
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
    DATA,
    ATTR_BATTERY_LOW_THRESHOLD,
)

from .common import isfloat

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

    if device_registry.async_get(device_id):
        device_registry.async_update_device(device_id, add_config_entry_id=entry.entry_id)
        return device_id
    return None

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

    if not device_id:
        return

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
                )
            ]
        )


async def async_setup_platform(
    hass: HomeAssistant,
) -> None:
    """Set up the battery note sensor."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)


class BatteryNotesBatteryLowSensor(BinarySensorEntity, CoordinatorEntity[BatteryNotesCoordinator]):
    """Represents a low battery threshold binary sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesBinarySensorEntityDescription,
        unique_id: str,
    ) -> None:
        """Create a low battery binary sensor."""

        device_registry = dr.async_get(hass)

        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_has_entity_name = True

        super().__init__(coordinator=coordinator)

        if coordinator.device_id and (
            device_entry := device_registry.async_get(coordinator.device_id)
        ):
            self._attr_device_info = DeviceInfo(
                connections=device_entry.connections,
                identifiers=device_entry.identifiers,
            )

            self.entity_id = f"binary_sensor.{coordinator.device_name.lower()}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        await super().async_added_to_hass()

        await self.coordinator.async_config_entry_first_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if (
            (
                wrapped_battery_state := self.hass.states.get(
                    self.coordinator.wrapped_battery.entity_id
                )
            )
            is None
            or wrapped_battery_state.state
            in [
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ]
            or not isfloat(wrapped_battery_state.state)
        ):
            self._attr_is_on = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        self._attr_is_on = self.coordinator.battery_low

        self.async_write_ha_state()

        _LOGGER.debug("%s binary sensor battery_low set to: %s", self.coordinator.wrapped_battery.entity_id, self.coordinator.battery_low)

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

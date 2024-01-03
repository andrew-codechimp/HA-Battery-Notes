"""Button platform for battery_notes."""
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
from homeassistant.components.button import (
    PLATFORM_SCHEMA,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
)

from homeassistant.helpers.reload import async_setup_reload_service

from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICE_ID,
)

from . import PLATFORMS

from .const import (
    DOMAIN,
    DOMAIN_CONFIG,
    DATA_COORDINATOR,
    CONF_ENABLE_REPLACED,
)

from .coordinator import BatteryNotesCoordinator

from .entity import (
    BatteryNotesEntityDescription,
)


@dataclass
class BatteryNotesButtonEntityDescription(
    BatteryNotesEntityDescription,
    ButtonEntityDescription,
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

    description = BatteryNotesButtonEntityDescription(
        unique_id_suffix="_battery_replaced_button",
        key="battery_replaced",
        translation_key="battery_replaced",
        icon="mdi:battery-sync",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=enable_replaced,
    )

    async_add_entities(
        [
            BatteryNotesButton(
                hass,
                description,
                f"{config_entry.entry_id}{description.unique_id_suffix}",
                device_id,
            )
        ]
    )


async def async_setup_platform(
    hass: HomeAssistant,
) -> None:
    """Set up the battery note sensor."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)


class BatteryNotesButton(ButtonEntity):
    """Represents a battery replaced button."""

    _attr_should_poll = False

    entity_description: BatteryNotesButtonEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        description: BatteryNotesButtonEntityDescription,
        unique_id: str,
        device_id: str,
    ) -> None:
        """Create a battery replaced button."""
        device_registry = dr.async_get(hass)

        self.entity_description = description
        self._attr_unique_id = unique_id
        self._attr_has_entity_name = True
        self._device_id = device_id

        if device_id and (device := device_registry.async_get(device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )

            self.entity_id = f"button.{device.name}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._attr_unique_id},
            )

    async def async_press(self) -> None:
        """Press the button."""
        device_id = self._device_id

        device_entry = {"battery_last_replaced": datetime.utcnow()}

        coordinator: BatteryNotesCoordinator = self.hass.data[DOMAIN][DATA_COORDINATOR]
        coordinator.async_update_device_config(device_id=device_id, data=device_entry)
        await coordinator.async_request_refresh()

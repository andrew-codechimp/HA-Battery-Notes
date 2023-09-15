"""Button platform for battery_notes."""
from __future__ import annotations

from dataclasses import dataclass

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
    ButtonDeviceClass,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_entity_registry_updated_event,
)

from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import (
    ConfigType,
)

from homeassistant.const import (
    CONF_NAME,
    CONF_UNIQUE_ID,
)


from . import PLATFORMS

from .const import (
    DOMAIN,
    CONF_BATTERY_TYPE,
    CONF_DEVICE_ID,
)

from .entity import (
    BatteryNotesEntityDescription,
)

ICON = "mdi:battery-sync"

@dataclass
class BatteryNotesButtonEntityDescription(
    ButtonEntityDescription, BatteryNotesEntityDescription
):
    """Describes Battery Notes button entity."""
    unique_id_suffix: str

ENTITY_DESCRIPTIONS: tuple[BatteryNotesButtonEntityDescription, ...] = (
    BatteryNotesButtonEntityDescription(
        unique_id_suffix="_battery_changed_button",
        key="battery_changed",
        name="Battery changed",
        icon="mdi:battery-sync",
        # entity_registry_enabled_default=False,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string
    }
)

@callback
def async_add_to_device(
    hass: HomeAssistant, entry: ConfigEntry
) -> str | None:
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
    battery_type = config_entry.data.get(CONF_BATTERY_TYPE)

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

    async_add_entities(
        BatteryNotesButton(hass, description, config_entry.title, f"{config_entry.entry_id}{description.unique_id_suffix}", device_id) for description in ENTITY_DESCRIPTIONS
    )

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the battery type button."""
    name: str | None = config.get(CONF_NAME)
    device_id: str = config[CONF_DEVICE_ID]

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

    async_add_entities(
        BatteryNotesButton(hass, description, name, f"{config.get(CONF_UNIQUE_ID)}{description.unique_id_suffix}", device_id) for description in ENTITY_DESCRIPTIONS
    )

class BatteryNotesButton(ButtonEntity):
    """Represents a battery changed button."""

    _attr_should_poll = False

    entity_description: BatteryNotesButtonEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        description: BatteryNotesButtonEntityDescription,
        name: str,
        unique_id: str,
        device_id: str,
    ) -> None:
        """Create a battery changed button."""
        device_registry = dr.async_get(hass)

        self.entity_description = description

        self._attr_name = f"{name} {description.name}"
        self._attr_unique_id = unique_id
        # self._attr_translation_key = "battery_changed"
        # self._attr_has_entity_name = False
        self._device_id = device_id

        self._device_id = device_id
        if device_id and (device := device_registry.async_get(device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )
        self._attr_entity_category = EntityCategory.DIAGNOSTIC


    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._attr_unique_id},
            )

    async def async_press(self) -> None:
        """Press the button."""
        await self.entity_description.press_fn(self.hass)

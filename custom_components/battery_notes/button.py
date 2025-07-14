"""Button platform for battery_notes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import voluptuous as vol
from homeassistant.components.button import (
    PLATFORM_SCHEMA,
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
)
from homeassistant.core import Event, HomeAssistant, callback, split_entity_id
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
)
from homeassistant.helpers.reload import async_setup_reload_service

from . import PLATFORMS
from .common import utcnow_no_timezone
from .const import (
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_SOURCE_ENTITY_ID,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_REPLACED,
)
from .coordinator import BatteryNotesConfigEntry, BatteryNotesCoordinator
from .entity import (
    BatteryNotesEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class BatteryNotesButtonEntityDescription(
    BatteryNotesEntityDescription,
    ButtonEntityDescription,
):
    """Describes Battery Notes button entity."""

    unique_id_suffix: str


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_SOURCE_ENTITY_ID): cv.string,
    }
)


@callback
def async_add_to_device(hass: HomeAssistant, entry: BatteryNotesConfigEntry) -> str | None:
    """Add our config entry to the device."""
    device_registry = dr.async_get(hass)

    device_id = entry.data.get(CONF_DEVICE_ID)

    if device_id:
        if device_registry.async_get(device_id):
            device_registry.async_update_device(
                device_id, add_config_entry_id=entry.entry_id
            )
            return device_id
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BatteryNotesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    device_id = config_entry.data.get(CONF_DEVICE_ID, None)

    async def async_registry_updated(event: Event[er.EventEntityRegistryUpdatedData]) -> None:
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
                not (entity_entry := entity_registry.async_get(data["entity_id"]))
                or not device_registry.async_get(device_id)
                or entity_entry.device_id == device_id
            ):
                # No need to do any cleanup
                return

            device_registry.async_update_device(
                device_id, remove_config_entry_id=config_entry.entry_id
            )

    coordinator = config_entry.runtime_data.coordinator
    assert(coordinator)

    config_entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, config_entry.entry_id, async_registry_updated
        )
    )

    if not coordinator.fake_device:
        device_id = async_add_to_device(hass, config_entry)

        if not device_id:
            return

    description = BatteryNotesButtonEntityDescription(
        unique_id_suffix="_battery_replaced_button",
        key="battery_replaced",
        translation_key="battery_replaced",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=config_entry.runtime_data.domain_config.enable_replaced,
    )

    async_add_entities(
        [
            BatteryNotesButton(
                hass,
                coordinator,
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
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesButtonEntityDescription,
        unique_id: str,
        device_id: str,
    ) -> None:
        """Create a battery replaced button."""

        super().__init__()

        device_registry = dr.async_get(hass)

        self.coordinator = coordinator

        self._attr_has_entity_name = True

        if coordinator.source_entity_id and not coordinator.device_id:
            self._attr_translation_placeholders = {
                "device_name": coordinator.device_name + " "
            }
            self.entity_id = (
                f"button.{coordinator.device_name.lower()}_{description.key}"
            )
        elif coordinator.source_entity_id and coordinator.device_id:
            source_entity_domain, source_object_id = split_entity_id(
                coordinator.source_entity_id
            )
            self._attr_translation_placeholders = {
                "device_name": coordinator.source_entity_name + " "
            }
            self.entity_id = f"button.{source_object_id}_{description.key}"
        else:
            self._attr_translation_placeholders = {"device_name": ""}
            self.entity_id = (
                f"button.{coordinator.device_name.lower()}_{description.key}"
            )

        self.entity_description = description
        self._attr_unique_id = unique_id
        self._device_id = device_id
        self._source_entity_id = coordinator.source_entity_id

        if device_id and (device := device_registry.async_get(device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
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

    async def async_press(self) -> None:
        """Press the button."""
        self.coordinator.last_replaced = utcnow_no_timezone()

        self.hass.bus.async_fire(
            EVENT_BATTERY_REPLACED,
            {
                ATTR_DEVICE_ID: self.coordinator.device_id or "",
                ATTR_SOURCE_ENTITY_ID: self.coordinator.source_entity_id
                or "",
                ATTR_DEVICE_NAME: self.coordinator.device_name,
                ATTR_BATTERY_TYPE_AND_QUANTITY: self.coordinator.battery_type_and_quantity,
                ATTR_BATTERY_TYPE: self.coordinator.battery_type,
                ATTR_BATTERY_QUANTITY: self.coordinator.battery_quantity,
            },
        )

        _LOGGER.debug(
            "Raised event battery replaced %s",
            self.coordinator.device_id,
        )

        await self.coordinator.async_request_refresh()

"""Button platform for battery_notes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.core import HomeAssistant, callback, split_entity_id
from homeassistant.const import (
    CONF_DEVICE_ID,
)
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DOMAIN,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_QUANTITY,
    ATTR_SOURCE_ENTITY_ID,
    SUBENTRY_BATTERY_NOTE,
    EVENT_BATTERY_REPLACED,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
)
from .common import utcnow_no_timezone
from .entity import BatteryNotesEntity, BatteryNotesEntityDescription
from .coordinator import BatteryNotesConfigEntry, BatteryNotesSubentryCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class BatteryNotesButtonEntityDescription(
    BatteryNotesEntityDescription,
    ButtonEntityDescription,
):
    """Describes Battery Notes button entity."""

    unique_id_suffix: str


@callback
def async_add_to_device(
    hass: HomeAssistant, entry: BatteryNotesConfigEntry
) -> str | None:
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
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""

    for subentry in config_entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_BATTERY_NOTE:
            continue

        assert config_entry.runtime_data.subentry_coordinators
        coordinator = config_entry.runtime_data.subentry_coordinators.get(
            subentry.subentry_id
        )
        assert coordinator

        if coordinator.is_orphaned:
            _LOGGER.debug(
                "Skipping button creation for orphaned entry: %s",
                subentry.title,
            )
            continue

        description = BatteryNotesButtonEntityDescription(
            unique_id_suffix="_battery_replaced_button",
            key="battery_replaced",
            translation_key="battery_replaced",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_registry_enabled_default=config_entry.runtime_data.domain_config.enable_replaced,
            entity_type="button",
        )

        async_add_entities(
            [
                BatteryNotesButton(
                    hass,
                    coordinator,
                    description,
                    f"{subentry.unique_id}{description.unique_id_suffix}",
                )
            ],
            config_subentry_id=subentry.subentry_id,
        )


class BatteryNotesButton(BatteryNotesEntity, ButtonEntity):
    """Represents a battery replaced button."""

    _attr_should_poll = False
    entity_description: BatteryNotesButtonEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BatteryNotesSubentryCoordinator,
        entity_description: BatteryNotesButtonEntityDescription,
        unique_id: str,
    ) -> None:
        """Create a battery replaced button."""

        super().__init__(
            hass=hass, entity_description=entity_description, coordinator=coordinator
        )

        if coordinator.source_entity_id and not coordinator.device_id:
            self._attr_translation_placeholders = {
                "device_name": coordinator.device_name + " "
            }
            self.entity_id = (
                f"button.{coordinator.device_name.lower()}_{entity_description.key}"
            )
        elif coordinator.source_entity_id and coordinator.device_id:
            _, source_object_id = split_entity_id(coordinator.source_entity_id)
            self._attr_translation_placeholders = {
                "device_name": coordinator.source_entity_name + " "
            }
            self.entity_id = f"button.{source_object_id}_{entity_description.key}"
        else:
            self._attr_translation_placeholders = {"device_name": ""}
            self.entity_id = (
                f"button.{coordinator.device_name.lower()}_{entity_description.key}"
            )

        self._attr_unique_id = unique_id
        self._source_entity_id = coordinator.source_entity_id

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
                ATTR_SOURCE_ENTITY_ID: self.coordinator.source_entity_id or "",
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

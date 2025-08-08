"""Entity for battery_notes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device import async_entity_id_to_device_id
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import BatteryNotesCoordinator


@dataclass(frozen=True, kw_only=True)
class BatteryNotesRequiredKeysMixin:
    """Mixin for required keys."""

    unique_id_suffix: str


@dataclass(frozen=True, kw_only=True)
class BatteryNotesEntityDescription(EntityDescription, BatteryNotesRequiredKeysMixin):
    """Generic Battery Notes entity description."""


class BatteryNoteEntity(CoordinatorEntity[BatteryNotesCoordinator]):
    """Base class for Battery Notes entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BatteryNotesCoordinator,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)

        device_registry = dr.async_get(hass)

        self.coordinator = coordinator
        self._attr_has_entity_name = True

        # Set up entity naming and translation placeholders
        # self._setup_entity_naming(description)

        # Set up device association
        self._setup_device_association(hass, device_registry)

    # def _setup_entity_naming(self, description: BatteryNotesEntityDescription) -> None:
    #     """Set up entity naming and translation placeholders."""
    #     if self.coordinator.source_entity_id and not self.coordinator.device_id:
    #         self._attr_translation_placeholders = {
    #             "device_name": self.coordinator.device_name + " "
    #         }
    #         self.entity_id = (
    #             f"sensor.{self.coordinator.device_name.lower()}_{description.key}"
    #         )
    #     elif self.coordinator.source_entity_id and self.coordinator.device_id:
    #         source_entity_domain, source_object_id = split_entity_id(
    #             self.coordinator.source_entity_id
    #         )
    #         self._attr_translation_placeholders = {
    #             "device_name": self.coordinator.source_entity_name + " "
    #         }
    #         self.entity_id = f"sensor.{source_object_id}_{description.key}"
    #     else:
    #         self._attr_translation_placeholders = {"device_name": ""}
    #         self.entity_id = (
    #             f"sensor.{self.coordinator.device_name.lower()}_{description.key}"
    #         )

    def _setup_device_association(
        self, hass: "HomeAssistant", device_registry: dr.DeviceRegistry
    ) -> None:
        """Set up device association."""
        if self.coordinator.device_id and (
            device_registry.async_get(self.coordinator.device_id)
        ):
            # Attach to the device_id
            self.device_entry = device_registry.async_get(self.coordinator.device_id)
        elif self.coordinator.source_entity_id:
            device_id = async_entity_id_to_device_id(
                hass, self.coordinator.source_entity_id
            )
            # source_entity_id is attached to a device, use that and add
            if device_id and (device_entry := device_registry.async_get(device_id)):
                self.device_entry = device_entry
        else:
            # No device, leave hanging
            self.device_entry = None

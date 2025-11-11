"""Entity for battery_notes."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant, split_entity_id
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device import async_entity_id_to_device_id
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import BatteryNotesSubentryCoordinator


@dataclass(frozen=True, kw_only=True)
class BatteryNotesRequiredKeysMixin:
    """Mixin for required keys."""

    unique_id_suffix: str
    entity_type: str
    require_device: bool = False


@dataclass(frozen=True, kw_only=True)
class BatteryNotesEntityDescription(EntityDescription, BatteryNotesRequiredKeysMixin):
    """Generic Battery Notes entity description."""


class BatteryNotesEntity(CoordinatorEntity[BatteryNotesSubentryCoordinator]):
    """Base class for Battery Notes entities."""

    coordinator: BatteryNotesSubentryCoordinator
    entity_description: BatteryNotesEntityDescription

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: BatteryNotesEntityDescription,
        coordinator: BatteryNotesSubentryCoordinator,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)

        device_registry = dr.async_get(hass)

        self.entity_description = entity_description
        self.coordinator = coordinator

        self._attr_has_entity_name = True

        # Set up entity naming and translation placeholders
        self._set_entity_id(entity_description)

        # Set up device association
        self._associate_device(hass, device_registry)

    def _set_entity_id(self, entity_description: BatteryNotesEntityDescription) -> None:
        """Set up entity naming and translation placeholders."""
        if self.coordinator.source_entity_id and not self.coordinator.device_id:
            self._attr_translation_placeholders = {
                "device_name": self.coordinator.device_name + " "
            }
            self.entity_id = f"{entity_description.entity_type}.{self.coordinator.device_name.lower()}_{entity_description.key}"
        elif self.coordinator.source_entity_id and self.coordinator.device_id:
            _, source_object_id = split_entity_id(self.coordinator.source_entity_id)
            self._attr_translation_placeholders = {
                "device_name": self.coordinator.source_entity_name + " "
            }
            self.entity_id = f"{entity_description.entity_type}.{source_object_id}_{entity_description.key}"
        else:
            self._attr_translation_placeholders = {"device_name": ""}
            self.entity_id = f"{entity_description.entity_type}.{self.coordinator.device_name.lower()}_{entity_description.key}"

    def _associate_device(
        self, hass: HomeAssistant, device_registry: dr.DeviceRegistry
    ) -> None:
        """Set up device association."""
        if self.coordinator.device_id and (
            device_registry.async_get(self.coordinator.device_id)
        ):
            # Attach to the device_id
            self.device_entry = device_registry.async_get(self.coordinator.device_id)
        elif (
            self.entity_description.require_device is False
            and self.coordinator.source_entity_id
        ):
            device_id = async_entity_id_to_device_id(
                hass, self.coordinator.source_entity_id
            )
            # source_entity_id is attached to a device, use that and add
            if device_id and (device_entry := device_registry.async_get(device_id)):
                self.device_entry = device_entry
        else:
            # No device, leave hanging
            self.device_entry = None

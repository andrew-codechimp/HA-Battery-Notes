"""Entity for battery_notes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import override

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device import async_entity_id_to_device_id
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .common import is_composite_device_id
from .coordinator import BatteryNotesDomainConfig, BatteryNotesSubentryCoordinator


@dataclass(frozen=True, kw_only=True)
class BatteryNotesRequiredKeysMixin:
    """Mixin for required keys."""

    unique_id_suffix: str
    object_id_base: str  # Used for entity id generation
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

        self.entity_description = entity_description
        self.coordinator = coordinator

        self._attr_has_entity_name = True

        self._associate_device(hass)
        self._attr_translation_placeholders = self._generate_translation_placeholders()

    @property
    @override
    def suggested_object_id(self) -> str:
        """Use English entity components while HA applies the entity ID format."""
        name = self.entity_description.object_id_base
        return slugify(f"{self._attr_translation_placeholders['device_name']}{name}")

    @property
    def domain_config(self) -> BatteryNotesDomainConfig:
        """Return the integration options shared by all battery notes."""
        return self.coordinator.config_entry.runtime_data.domain_config

    @property
    def available(self) -> bool:
        """Return if entity is available.

        CoordinatorEntity only reports the coordinator update status, also honour
        _attr_available which entities clear while their source is unavailable.
        """
        return super().available and self._attr_available

    def _associate_device(self, hass: HomeAssistant) -> None:
        """Set up device association."""

        device_registry = dr.async_get(hass)
        # HACK: HA 2026.8 splits composite devices into multiple devices, so we need to check if the device_id is a composite device
        if (
            self.coordinator.device_id
            and (device_entry := device_registry.async_get(self.coordinator.device_id))
            and not is_composite_device_id(hass, self.coordinator.device_id)
        ):
            # Attach to the device_id
            self.device_entry = device_entry
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

    def _generate_translation_placeholders(self) -> Mapping[str, str]:
        """Generate translation placeholders."""
        if self.device_entry is None:
            return {"device_name": self.coordinator.device_name + " "}
        if self.coordinator.source_entity_id and (
            source_name := self.coordinator.source_entity_name
        ):
            return {"device_name": source_name + " "}
        return {"device_name": ""}

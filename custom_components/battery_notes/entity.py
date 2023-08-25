"""Base entity for the Battery Notes integration."""
from __future__ import annotations

from typing import Any
from datetime import datetime, timedelta

from homeassistant.components.homeassistant import exposed_entities
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_UNAVAILABLE,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity import DeviceInfo, Entity, EntityCategory
from homeassistant.helpers.event import async_track_state_change_event

from .const import DOMAIN


class BaseEntity(Entity):
    """Represents a Battery Note Entity."""

    _attr_should_poll = False
    _is_new_entity: bool

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_title: str,
        domain: str,
        entity_id: str,
        unique_id: str,
        device_id: str,
    ) -> None:
        """Initialize Battery Type."""
        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)
        battery_note_entity = entity_registry.async_get(entity_id)
        # device_id = battery_note_entity.device_id if battery_note_entity else None
        entity_category = battery_note_entity.entity_category if battery_note_entity else None
        has_entity_name = battery_note_entity.has_entity_name if battery_note_entity else False

        name: str | None = config_entry_title
        if battery_note_entity:
            name = battery_note_entity.original_name

        self._device_id = device_id
        if device_id and (device := device_registry.async_get(device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )
        self._attr_entity_category = EntityCategory.DIAGNOSTIC
        self._attr_has_entity_name = has_entity_name
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._battery_note_entity_id = entity_id
        self._attr_icon = "mdi:battery-unknown"
        self._attr_should_poll = False

        self._is_new_entity = (
            entity_registry.async_get_entity_id(domain, DOMAIN, unique_id) is None
        )

    @callback
    def async_state_changed_listener(self, event: Event | None = None) -> None:
        """Handle child updates."""
        if (
            state := self.hass.states.get(self._battery_note_entity_id)
        ) is None or state.state == STATE_UNAVAILABLE:
            self._attr_available = False
            return

        self._attr_available = True

    @callback
    def handle_event_callback(self, event):
        """Handle incoming event for device type."""

        # Propagate changes through ha
        self.async_schedule_update_ha_state(True)


    async def async_added_to_hass(self) -> None:
        """Register callbacks and copy the wrapped entity's custom name if set."""

        @callback
        def _async_state_changed_listener(event: Event | None = None) -> None:
            """Handle child updates."""
            print("Here at state change")
            self.async_state_changed_listener(event)
            self.async_write_ha_state()
            self.async_schedule_update_ha_state(True)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._battery_note_entity_id], _async_state_changed_listener
            )
        )

        # Call once on adding
        _async_state_changed_listener()

        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._battery_note_entity_id},
            )

        if not self._is_new_entity or not (
            wrapped_switch := registry.async_get(self._battery_note_entity_id)
        ):
            return

        def copy_custom_name(wrapped_switch: er.RegistryEntry) -> None:
            """Copy the name set by user from the wrapped entity."""
            if wrapped_switch.name is None:
                return
            registry.async_update_entity(self.entity_id, name=wrapped_switch.name)

        def copy_expose_settings() -> None:
            """Copy assistant expose settings from the wrapped entity.

            Also unexpose the wrapped entity if exposed.
            """
            expose_settings = exposed_entities.async_get_entity_settings(
                self.hass, self._battery_note_entity_id
            )
            for assistant, settings in expose_settings.items():
                if (should_expose := settings.get("should_expose")) is None:
                    continue
                exposed_entities.async_expose_entity(
                    self.hass, assistant, self.entity_id, should_expose
                )
                exposed_entities.async_expose_entity(
                    self.hass, assistant, self._battery_note_entity_id, False
                )

        copy_custom_name(wrapped_switch)
        copy_expose_settings()


    # @callback
    # def async_state_changed_listener(self, event: Event | None = None) -> None:
    #     """Handle child updates."""
    #     super().async_state_changed_listener(event)
    #     if (
    #         not self.available
    #         or (state := self.hass.states.get(self._battery_note_entity_id)) is None
    #     ):
    #         return

    #     self._attr_is_on = state.state == STATE_ON

    # @callback
    # def async_update(self, event_time: datetime | None = None) -> None:
    #     """Update the entity."""
    #     self.async_schedule_update_ha_state(True)

    @callback
    def async_update_callback(self, reason):
        """Update the device's state."""
        self.async_schedule_update_ha_state()

"""Diagnostic helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
)

from .common import get_device_model_id
from .const import CONF_SOURCE_ENTITY_ID
from .coordinator import BatteryNotesConfigEntry, BatteryNotesSubentryCoordinator
from .library import DATA_LIBRARY, Library, ModelInfo


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: BatteryNotesConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    library = hass.data.get(DATA_LIBRARY)
    coordinators = config_entry.runtime_data.subentry_coordinators or {}

    diagnostics: dict[str, Any] = {"entry": config_entry.as_dict()}
    battery_notes: dict[str, Any] = {}

    for subentry in config_entry.subentries.values():
        device_id = subentry.data.get(CONF_DEVICE_ID, None)
        source_entity_id = subentry.data.get(CONF_SOURCE_ENTITY_ID, None)

        if source_entity_id:
            entity = entity_registry.async_get(source_entity_id)
            if entity:
                device_id = entity.device_id

        device_entry = device_registry.async_get(device_id) if device_id else None
        if device_entry:
            device_info = {
                "manufacturer": device_entry.manufacturer,
                "model": device_entry.model,
                "model_id": get_device_model_id(device_entry),
                "hw_version": device_entry.hw_version,
            }
            diagnostics.update({f"subentry {subentry.subentry_id}": device_info})

        if coordinator := coordinators.get(subentry.subentry_id):
            battery_notes[subentry.subentry_id] = {
                **_coordinator_diagnostics(coordinator),
                "library_match": await _library_match(library, device_entry),
            }

    diagnostics["library_loaded"] = library is not None and library.is_loaded
    diagnostics["battery_notes"] = battery_notes

    return diagnostics


def _coordinator_diagnostics(
    coordinator: BatteryNotesSubentryCoordinator,
) -> dict[str, Any]:
    """Return the runtime state of a battery note."""
    data: dict[str, Any] = {
        "orphaned": coordinator.is_orphaned,
        "wrapped_battery": _entity_id(coordinator.wrapped_battery),
        "wrapped_battery_low": _entity_id(coordinator.wrapped_battery_low),
    }
    if coordinator.is_orphaned:
        return data

    return {
        **data,
        "battery_low_threshold": coordinator.battery_low_threshold,
        "battery_increased_threshold": coordinator.battery_increased_threshold,
        "battery_low_template": coordinator.battery_low_template,
        "battery_percentage_template": coordinator.battery_percentage_template,
        "retain_state": coordinator.retain_state,
        "current_battery_level": coordinator.current_battery_level,
        "battery_low": coordinator.battery_low,
        "last_reported": _isoformat(coordinator.last_reported),
        "last_reported_level": coordinator.last_reported_level,
        "last_replaced": _isoformat(coordinator.last_replaced),
    }


async def _library_match(
    library: Library | None, device_entry: dr.DeviceEntry | None
) -> dict[str, Any] | None:
    """Return the library entry matching the source device, if any."""
    if (
        library is None
        or not library.is_loaded
        or device_entry is None
        or not device_entry.manufacturer
        or not device_entry.model
    ):
        return None

    details = await library.get_device_battery_details(
        ModelInfo(
            device_entry.manufacturer,
            device_entry.model,
            get_device_model_id(device_entry),
            device_entry.hw_version,
        )
    )
    return details._asdict() if details else None


def _entity_id(entity_entry: er.RegistryEntry | None) -> str | None:
    return entity_entry.entity_id if entity_entry else None


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None

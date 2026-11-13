"""Common functions for battery_notes."""

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntry

from .store import BatteryNotesStorage


@callback
def async_hide_source_battery(
    hass: HomeAssistant,
    store: BatteryNotesStorage,
    subentry_id: str,
    entity_id: str,
) -> None:
    """Hide a visible source and remember which note hid it."""
    registry = er.async_get(hass)
    entity = registry.async_get(entity_id)
    if entity is None or entity.hidden_by is not None:
        return

    store.async_set_hidden_entities(
        subentry_id, store.hidden_entities.get(subentry_id, set()) | {entity.id}
    )
    registry.async_update_entity(
        entity.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION
    )


@callback
def async_unhide_source_batteries(
    hass: HomeAssistant,
    store: BatteryNotesStorage,
    subentry_id: str,
    keep_hidden: set[str] | None = None,
) -> None:
    """Restore only sources hidden by this note, preserving user hiding."""
    registry = er.async_get(hass)
    hidden_entities = store.hidden_entities.get(subentry_id, set())
    retained = hidden_entities & (keep_hidden or set())
    for registry_id in hidden_entities - retained:
        entity = registry.async_get(registry_id)
        if entity and entity.hidden_by == er.RegistryEntryHider.INTEGRATION:
            registry.async_update_entity(entity.entity_id, hidden_by=None)
    store.async_set_hidden_entities(subentry_id, retained)


def validate_is_float(num):
    """Validate value is a float."""
    if num is not None:
        try:
            float(num)
            return True
        except ValueError:
            return False
    return False


def get_device_model_id(device_entry: DeviceEntry) -> str | None:
    """Get the device model if available."""
    return device_entry.model_id if hasattr(device_entry, "model_id") else None


def get_related_device_ids(hass: HomeAssistant, device_id: str) -> set[str]:
    """Return the IDs of all devices representing the same physical device, including `device_id` itself.

    Devices are related when they were split off from the same legacy composite device, or when they
    share any identifier or connection. Both happen when a single physical device is provided by more
    than one config entry.
    `device_id` may be the ID of a registered device, or of a legacy composite device.
    """
    device_registry = dr.async_get(hass)
    related = {device_id}
    related.update(
        device.id for device in _get_composite_split_devices(device_registry, device_id)
    )

    device = device_registry.async_get(device_id, include_child_devices=False)
    if device is None:
        return related

    sibling_devices = _get_composite_split_devices(
        device_registry, device.composite_device_id
    )
    related.update(sibling_device.id for sibling_device in sibling_devices)

    related.update(
        linked_device.id
        for linked_device in device_registry.async_get_devices(
            identifiers=device.identifiers, connections=device.connections
        )
    )

    return related


def _get_composite_split_devices(
    device_registry: dr.DeviceRegistry,
    device_id: str | None,
) -> list[DeviceEntry]:
    """Return all devices split off from the same legacy composite device as the given device.

    Accepts either the composite device ID itself, or the ID of one of the split devices.
    Returns an empty list when the device is unrelated to a composite device.
    """
    if not device_id:
        return []

    if split_devices := device_registry.async_get_devices_for_composite_device_id(
        device_id
    ):
        return split_devices

    # Not a composite ID itself, so it may be one of the devices split off from a composite.
    device = device_registry.async_get(device_id, include_child_devices=False)
    composite_device_id = device.composite_device_id if device else None
    if not composite_device_id:
        return []
    return device_registry.async_get_devices_for_composite_device_id(
        composite_device_id
    )


def is_composite_device_id(hass: HomeAssistant, device_id: str) -> bool:
    """Return whether a device ID identifies a legacy composite device."""
    device_registry = dr.async_get(hass)

    return (
        device_registry.async_get(device_id, include_composite_devices=False) is None
        and device_registry.async_get(device_id) is not None
    )


def composite_device_issue_id(config_subentry_id: str) -> str:
    """Return the repair issue ID for a config subentry using a composite device ID."""
    return f"composite_device_id_{config_subentry_id}"


def missing_device_issue_id(config_subentry_id: str) -> str:
    """Return the repair issue ID for a config subentry with a missing device."""
    return f"missing_device_{config_subentry_id}"

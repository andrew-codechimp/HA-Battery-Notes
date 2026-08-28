"""Common functions for battery_notes."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceEntry


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

    device = device_registry.async_get(device_id)
    if device is None:
        return related

    sibling_devices = _get_composite_split_devices(
        device_registry, getattr(device, "composite_device_id", None)
    )
    related.update(sibling_device.id for sibling_device in sibling_devices)

    # HACK: Only available in HA >=2026.8. On older versions devices sharing an identifier or connection
    # were merged into a single device, so there is nothing to relate.
    get_devices = getattr(device_registry, "async_get_devices", None)
    if callable(get_devices):
        related.update(
            linked_device.id
            for linked_device in get_devices(
                identifiers=device.identifiers, connections=device.connections
            )
        )

    return related


def _get_composite_split_devices(
    device_registry: dr.DeviceRegistry,
    device_id: str | None,
) -> list[DeviceEntry]:
    """HACK: Return all devices split off from the same legacy composite device as the given device.

    Accepts either the composite device ID itself, or the ID of one of the split devices.
    Returns an empty list when the device is unrelated to a composite device, or when running on
    HA <2026.8, which does not split composite devices at all.
    """
    if not device_id:
        return []

    get_split_devices = getattr(
        device_registry, "async_get_devices_for_composite_device_id", None
    )
    if not callable(get_split_devices):
        return []

    if split_devices := list(get_split_devices(device_id)):
        return split_devices

    # Not a composite ID itself, so it may be one of the devices split off from a composite.
    device = device_registry.async_get(device_id)
    composite_device_id = (
        getattr(device, "composite_device_id", None) if device else None
    )
    if not composite_device_id:
        return []
    return list(get_split_devices(composite_device_id))


def is_composite_device_id(hass: HomeAssistant, device_id: str) -> bool:
    """HACK: Return whether a device ID identifies a legacy composite device.

    A composite device ID resolves with async_get(device_id) but not with
    async_get(device_id, include_composite_devices=False).
    """
    device_registry = dr.async_get(hass)

    # HACK: Try the modern API first (HA 2026.9+)
    try:
        # If device exists without composites, it's not composite
        if device_registry.async_get(device_id, include_composite_devices=False):  # type: ignore[call-arg]
            return False
        # If it's None, check if device exists at all (composite if it does)
        return device_registry.async_get(device_id) is not None
    except TypeError:
        # Fallback for older versions (HA <2026.9) - include_composite_devices not supported
        pass

    # Fall back to deprecated method for older versions
    is_composite = getattr(device_registry, "async_is_composite_device_id", None)
    if callable(is_composite):
        return bool(is_composite(device_id))

    return False


def composite_device_issue_id(config_subentry_id: str) -> str:
    """Return the repair issue ID for a config subentry using a composite device ID."""
    return f"composite_device_id_{config_subentry_id}"


def missing_device_issue_id(config_subentry_id: str) -> str:
    """Return the repair issue ID for a config subentry with a missing device."""
    return f"missing_device_{config_subentry_id}"

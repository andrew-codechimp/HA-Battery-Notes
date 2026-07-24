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


def is_composite_device_id(hass: HomeAssistant, device_id: str) -> bool:
    """Return whether a device ID identifies a legacy composite device.

    Check for availability of async_is_composite_device_id, because this function is only available in HA >=2026.8
    """
    device_registry = dr.async_get(hass)
    is_composite = getattr(device_registry, "async_is_composite_device_id", None)
    if not callable(is_composite):
        return False
    return bool(is_composite(device_id))

"""Common functions for battery_notes."""

from datetime import datetime

from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.util import dt as dt_util


def validate_is_float(num):
    """Validate value is a float."""
    if num:
        try:
            float(num)
            return True
        except ValueError:
            return False
    return False

def utcnow_no_timezone() -> datetime:
    """Return UTC now without timezone information."""

    return dt_util.utcnow().replace(tzinfo=None)

def get_device_model_id(device_entry: DeviceEntry) -> str | None:
    """Get the device model if available."""
    return device_entry.model_id if hasattr(device_entry, "model_id") else None

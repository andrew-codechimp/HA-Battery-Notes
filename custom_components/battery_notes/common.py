"""Common functions for battery_notes."""

import re
from datetime import datetime

from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.util import dt as dt_util


def validate_is_float(num):
    """Validate value is a float."""
    if num is not None:
        try:
            float(num)
            return True
        except ValueError:
            return False
    return False


def utcnow_no_timezone() -> datetime:
    """Return UTC now without timezone information."""

    return dt_util.utcnow().replace(tzinfo=None)


def datetime_no_timezone(dt: datetime) -> datetime:
    """Return the datetime without timezone information."""

    return dt.replace(tzinfo=None)


def fix_datetime_string(datetime_str: str) -> str:
    """Fix datetime string by replacing colon with period before microseconds."""
    # Prior to 3.3.2 there was an issue where microseconds were formatted with a colon and are held in storage.
    # New dates are stored correctly, over time the last_reported, last_replaced will be updated with the correct format.

    # Look for timezone offset at the end (e.g., +00:00, -05:00, Z)
    tz_match = re.search(r"([+-]\d{2}:\d{2}|[+-]\d{4}|Z)$", datetime_str)

    if tz_match:
        # Split into datetime and timezone parts
        tz_start = tz_match.start()
        datetime_part = datetime_str[:tz_start]
        tz_part = datetime_str[tz_start:]
    else:
        datetime_part = datetime_str
        tz_part = ""

    # Replace colon with period only if followed by exactly 6 digits (microseconds)
    datetime_part = re.sub(r":(\d{6})$", r".\1", datetime_part)

    return datetime_part + tz_part


def get_device_model_id(device_entry: DeviceEntry) -> str | None:
    """Get the device model if available."""
    return device_entry.model_id if hasattr(device_entry, "model_id") else None

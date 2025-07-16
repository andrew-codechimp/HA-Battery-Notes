"""Common functions for battery_notes."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import Any

from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_device_registry_updated_event
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

def get_device_model_id(device_entry: dr.DeviceEntry) -> str | None:
    """Get the device model if available."""
    return device_entry.model_id if hasattr(device_entry, "model_id") else None

def async_handle_source_device_changes(
    hass: HomeAssistant,
    *,
    helper_config_entry_id: str,
    source_device_id: str,
    source_device_removed: Callable[[], Coroutine[Any, Any, None]],
) -> CALLBACK_TYPE:
    """Handle changes to a helper entity's source device.

    The following changes are handled:
    - Device removal: If the source device is removed:
      - source_device_removed is called to handle the removal.

    :param source_device_removed: A function which is called when the source device
        is removed. This can be used to clean up any resources related to the source
        device.
    """

    async def async_registry_updated(
        event: Event[dr.EventDeviceRegistryUpdatedData],
    ) -> None:
        """Handle device registry update."""
        nonlocal source_device_id

        data = event.data
        if data["action"] == "remove":
            await source_device_removed()

    return async_track_device_registry_updated_event(
        hass, source_device_id, async_registry_updated
    )

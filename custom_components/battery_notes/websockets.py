"""Websocket commands for Battery Notes."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN

WEBSOCKET_LIST_DEVICES = f"{DOMAIN}/list_devices"


@callback
@websocket_api.websocket_command({
    vol.Required("type"): WEBSOCKET_LIST_DEVICES,
})
def websocket_list_devices(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return Battery Notes devices with current battery percentage."""
    rows: list[dict[str, Any]] = []

    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        runtime_data = getattr(entry, "runtime_data", None)
        if runtime_data is None:
            continue

        subentry_coordinators = runtime_data.subentry_coordinators
        if not subentry_coordinators:
            continue

        for subentry_id, coordinator in subentry_coordinators.items():
            rows.append({
                "subentry_id": subentry_id,
                "device_name": coordinator.device_name,
                "battery_type": coordinator.battery_type,
                "battery_quantity": coordinator.battery_quantity,
                "battery_percentage": coordinator.rounded_battery_level,
                "battery_low": coordinator.battery_low,
                "last_replaced": coordinator.last_replaced.isoformat()
                if coordinator.last_replaced
                else None,
            })

    rows.sort(key=lambda row: str(row["device_name"]).lower())
    connection.send_result(msg["id"], rows)


@callback
def async_setup_websockets(hass: HomeAssistant) -> None:
    """Register websocket commands for Battery Notes."""
    websocket_api.async_register_command(hass, websocket_list_devices)

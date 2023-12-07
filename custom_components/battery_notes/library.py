"""Battery Type library for battery_notes."""
from __future__ import annotations

import json
import logging
import os
from typing import NamedTuple

BUILT_IN_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "../data")

_LOGGER = logging.getLogger(__name__)

async def get_device_battery_details(
    manufacturer: str,
    model: str,
) -> DeviceBatteryDetails | None:
    """Create a battery details object from the JSON data."""
    json_path = os.path.join(BUILT_IN_DATA_DIRECTORY, "library.json")

    try:
        with open(json_path, encoding="utf-8") as file:
            json_data = json.load(file)

            devices = json_data["devices"]
            for device in devices:
                if device["manufacturer"] == manufacturer and device["model"] == model:
                    device_battery_details = DeviceBatteryDetails(
                        manufacturer=device["manufacturer"],
                        model=device["model"],
                        battery_type=device["battery_type"],
                        battery_quantity=device["battery_quantity"],
                        )
                    return device_battery_details

    except FileNotFoundError:
        _LOGGER.error("library.json file not found in directory %s", BUILT_IN_DATA_DIRECTORY)
        return None

    return None


class DeviceBatteryDetails(NamedTuple):
    """Describes a device battery type."""

    manufacturer: str
    model: str
    battery_type: str
    battery_quantity: int

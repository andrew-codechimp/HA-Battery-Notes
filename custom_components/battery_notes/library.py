"""Battery Type library for battery_notes."""
from __future__ import annotations

import json
import logging
import os
from typing import NamedTuple

from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    DATA_LIBRARY,
    DOMAIN_CONFIG,
    CONF_USER_LIBRARY,
)

BUILT_IN_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "data")

_LOGGER = logging.getLogger(__name__)


class Library:  # pylint: disable=too-few-public-methods
    """Hold all known battery types."""

    _devices = []

    def __init__(self, hass: HomeAssistant) -> None:
        """Init."""

        # User Library
        if (
            DOMAIN_CONFIG in hass.data[DOMAIN]
            and CONF_USER_LIBRARY in hass.data[DOMAIN][DOMAIN_CONFIG]
            ):
            user_library_filename = hass.data[DOMAIN][DOMAIN_CONFIG].get(CONF_USER_LIBRARY)
            if  user_library_filename != "":
                json_user_path = os.path.join(
                    BUILT_IN_DATA_DIRECTORY,
                    user_library_filename,
                )
                _LOGGER.debug("Using user library file at %s", json_user_path)

                try:
                    with open(json_user_path, encoding="utf-8") as user_file:
                        user_json_data = json.load(user_file)
                        self._devices = user_json_data["devices"]
                        user_file.close()

                except FileNotFoundError:
                    _LOGGER.error(
                        "User library file not found at %s",
                        json_user_path,
                    )

        # Default Library
        json_default_path = os.path.join(
            BUILT_IN_DATA_DIRECTORY,
            "library.json",)

        _LOGGER.debug("Using library file at %s", json_default_path)

        try:
            with open(json_default_path, encoding="utf-8") as default_file:
                default_json_data = json.load(default_file)
                self._devices.extend(default_json_data["devices"])
                default_file.close()

        except FileNotFoundError:
            _LOGGER.error(
                "library.json file not found in directory %s",
                BUILT_IN_DATA_DIRECTORY,
            )

    @staticmethod
    def factory(hass: HomeAssistant) -> Library:
        """Return the library or create."""

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        if DATA_LIBRARY in hass.data[DOMAIN]:
            return hass.data[DOMAIN][DATA_LIBRARY]  # type: ignore

        library = Library(hass)
        hass.data[DOMAIN][DATA_LIBRARY] = library
        return library

    async def get_device_battery_details(
        self,
        manufacturer: str,
        model: str,
    ) -> DeviceBatteryDetails | None:
        """Create a battery details object from the JSON devices data."""

        if self._devices is not None:
            for device in self._devices:
                if (
                    str(device["manufacturer"] or "").casefold()
                    == str(manufacturer or "").casefold()
                    and str(device["model"] or "").casefold()
                    == str(model or "").casefold()
                ):
                    device_battery_details = DeviceBatteryDetails(
                        manufacturer=device["manufacturer"],
                        model=device["model"],
                        battery_type=device["battery_type"],
                        battery_quantity=device.get("battery_quantity", 1),
                    )
                    return device_battery_details

        return None

    def loaded(self) -> bool:
        """Library loaded successfully."""
        return self._devices is not None


class DeviceBatteryDetails(NamedTuple):
    """Describes a device battery type."""

    manufacturer: str
    model: str
    battery_type: str
    battery_quantity: int

    @property
    def is_manual(self):
        """Return whether the device should be discovered or battery type suggested."""
        if self.battery_type.casefold() == "manual".casefold():
            return True
        return False

    @property
    def battery_type_and_quantity(self):
        """Return battery type with quantity prefix."""
        try:
            quantity = int(self.battery_quantity)
        except ValueError:
            quantity = 0

        if quantity > 1:
            batteries = str(quantity) + "x " + self.battery_type
        else:
            batteries = self.battery_type

        return batteries


class ModelInfo(NamedTuple):
    """Describes a device."""

    manufacturer: str
    model: str

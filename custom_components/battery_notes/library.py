"""Battery Type library for battery_notes."""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Final, NamedTuple, cast
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey
from homeassistant.helpers.storage import STORAGE_DIR

from .const import DOMAIN
from .coordinator import MY_KEY

_LOGGER = logging.getLogger(__name__)

LIBRARY_DEVICES: Final[str] = "devices"
LIBRARY_MANUFACTURER: Final[str] = "manufacturer"
LIBRARY_MODEL: Final[str] = "model"
LIBRARY_MODEL_MATCH_METHOD: Final[str] = "model_match_method"
LIBRARY_MODEL_ID: Final[str] = "model_id"
LIBRARY_HW_VERSION: Final[str] = "hw_version"
LIBRARY_BATTERY_TYPE: Final[str] = "battery_type"
LIBRARY_BATTERY_QUANTITY: Final[str] = "battery_quantity"
LIBRARY_MISSING: Final[str] = "##MISSING##"

DATA_LIBRARY: HassKey[Library] = HassKey(f"{DOMAIN}_library")


@dataclass(frozen=True, kw_only=True)
class LibraryDevice:
    """Class for keeping track of a library device."""

    manufacturer: str
    model: str
    battery_type: str
    model_match_method: str | None = None
    model_id: str | None = None
    battery_quantity: int = 1
    hw_version: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> LibraryDevice:
        """Create LibraryDevice instance from JSON data."""
        return cls(
            manufacturer=data[LIBRARY_MANUFACTURER],
            model=data[LIBRARY_MODEL],
            model_match_method=data.get(LIBRARY_MODEL_MATCH_METHOD),
            model_id=data.get(LIBRARY_MODEL_ID),
            hw_version=data.get(LIBRARY_HW_VERSION),
            battery_type=data[LIBRARY_BATTERY_TYPE],
            battery_quantity=data.get(LIBRARY_BATTERY_QUANTITY, 1),
        )


class Library:  # pylint: disable=too-few-public-methods
    """Hold all known battery types."""

    _manufacturer_devices: dict[str, list[LibraryDevice]] = {}

    def __init__(self, hass: HomeAssistant) -> None:
        """Init."""
        self.hass = hass

    async def load_libraries(self):
        """Load the user and default libraries."""

        def _load_library_json(library_file: str) -> dict[str, Any]:
            """Load library json file."""
            with open(library_file, encoding="utf-8") as file:
                return cast(dict[str, Any], json.load(file))

        # User Library
        domain_config = self.hass.data.get(MY_KEY)
        if domain_config and domain_config.user_library != "":
            json_user_path = self.hass.config.path(
                STORAGE_DIR, "battery_notes", domain_config.user_library
            )
            _LOGGER.debug("Using user library file at %s", json_user_path)

            try:
                user_json_data = await self.hass.async_add_executor_job(
                    _load_library_json, json_user_path
                )

                for json_device in user_json_data["devices"]:
                    library_device = LibraryDevice.from_json(json_device)
                    manufacturer = library_device.manufacturer.casefold()
                    if manufacturer not in self._manufacturer_devices:
                        self._manufacturer_devices[manufacturer] = []
                    self._manufacturer_devices[manufacturer].append(library_device)
                _LOGGER.debug("Loaded %s user devices", len(user_json_data["devices"]))

            except FileNotFoundError:
                # Try to move the user library to new location
                try:
                    legacy_data_directory = os.path.join(
                        os.path.dirname(__file__), "data"
                    )
                    legacy_json_user_path = os.path.join(
                        legacy_data_directory, domain_config.user_library
                    )
                    os.makedirs(os.path.dirname(json_user_path), exist_ok=True)
                    os.rename(legacy_json_user_path, json_user_path)

                    _LOGGER.debug(
                        "User library moved to %s",
                        json_user_path,
                    )
                except FileNotFoundError:
                    _LOGGER.error(
                        "User library file not found at %s",
                        json_user_path,
                    )

        # Default Library
        json_default_path = self.hass.config.path(
            STORAGE_DIR, "battery_notes", "library.json"
        )

        _LOGGER.debug("Using library file at %s", json_default_path)

        try:
            default_json_data = await self.hass.async_add_executor_job(
                _load_library_json, json_default_path
            )
            for json_device in default_json_data["devices"]:
                library_device = LibraryDevice.from_json(json_device)
                manufacturer = library_device.manufacturer.casefold()
                if manufacturer not in self._manufacturer_devices:
                    self._manufacturer_devices[manufacturer] = []
                self._manufacturer_devices[manufacturer].append(library_device)
            _LOGGER.debug(
                "Loaded %s default devices", len(default_json_data[LIBRARY_DEVICES])
            )

        except FileNotFoundError:
            _LOGGER.error(
                "library.json file not found at %s",
                json_default_path,
            )

    async def get_device_battery_details(
        self,
        device_to_find: ModelInfo,
    ) -> DeviceBatteryDetails | None:
        """Create a battery details object from the JSON devices data."""

        if not bool(self._manufacturer_devices):
            return None

        # Test only
        # device_to_find = ModelInfo("Aqara", "Aqara Climate Sensor W100", "8196", None)
        # device_to_find = ModelInfo("Google", "Topaz-2.7", None, "Battery")
        # device_to_find = ModelInfo("Google", "Topaz-2.7", None, "Wired")
        # device_to_find = ModelInfo("Philips", "Hue dimmer switch (929002398602)", None, None)
        # device_to_find = ModelInfo("Philips", "Hue dimmer switch", "929002398602", None)
        # device_to_find = ModelInfo("Philips", "Hue dimmer switch", "929002398602", "1")

        # Get all devices matching manufacturer & model
        matching_devices = None
        partial_matching_devices = None
        fully_matching_devices = None

        manufacturer_devices = self._manufacturer_devices.get(
            device_to_find.manufacturer.casefold(), None
        )
        if not manufacturer_devices:
            return None

        matching_devices = [
            x
            for x in manufacturer_devices
            if self.device_basic_match(x, device_to_find)
        ]

        if matching_devices and len(matching_devices) > 1:
            partial_matching_devices = [
                x
                for x in matching_devices
                if self.device_partial_match(x, device_to_find)
            ]

        if partial_matching_devices and len(partial_matching_devices) > 0:
            matching_devices = partial_matching_devices

        if matching_devices and len(matching_devices) > 1:
            fully_matching_devices = [
                x for x in matching_devices if self.device_full_match(x, device_to_find)
            ]

        if fully_matching_devices and len(fully_matching_devices) > 0:
            matching_devices = fully_matching_devices

        if not matching_devices:
            return None

        if len(matching_devices) > 1:
            return None

        matched_device = matching_devices[0]

        return DeviceBatteryDetails(
            manufacturer=matched_device.manufacturer,
            model=matched_device.model,
            model_id=matched_device.model_id or "",
            hw_version=matched_device.hw_version or "",
            battery_type=matched_device.battery_type,
            battery_quantity=matched_device.battery_quantity,
        )

    @property
    def is_loaded(self) -> bool:
        """Library loaded successfully."""
        return bool(self._manufacturer_devices)

    def device_basic_match(
        self, library_device: LibraryDevice, device_to_find: ModelInfo
    ) -> bool:
        """Check if device match on manufacturer and model."""
        if (
            library_device.manufacturer.casefold()
            != device_to_find.manufacturer.casefold()
        ):
            return False

        if library_device.model_match_method:
            if library_device.model_match_method == "startswith":
                if (
                    str(device_to_find.model or "")
                    .casefold()
                    .startswith(library_device.model.casefold())
                ):
                    return True
            if library_device.model_match_method == "endswith":
                if (
                    str(device_to_find.model or "")
                    .casefold()
                    .endswith(library_device.model.casefold())
                ):
                    return True
            if library_device.model_match_method == "contains":
                if str(device_to_find.model or "").casefold() in (
                    library_device.model.casefold()
                ):
                    return True
        elif (
            library_device.model.casefold()
            == str(device_to_find.model or "").casefold()
        ):
            return True
        return False

    def device_partial_match(
        self, library_device: LibraryDevice, device_to_find: ModelInfo
    ) -> bool:
        """Check if device match on hw_version or model_id."""
        if device_to_find.hw_version is None and device_to_find.model_id is None:
            return bool(
                library_device.hw_version is None and library_device.model_id is None
            )

        if device_to_find.hw_version is None or device_to_find.model_id is None:
            if (library_device.hw_version or "").casefold() == str(
                device_to_find.hw_version
            ).casefold() or (library_device.model_id or "").casefold() == str(
                device_to_find.model_id
            ).casefold():
                return True

        return False

    def device_full_match(
        self, library_device: LibraryDevice, device_to_find: ModelInfo
    ) -> bool:
        """Check if device match on hw_version and model_id."""
        return bool(
            (library_device.hw_version or "").casefold()
            == str(device_to_find.hw_version).casefold()
            and (library_device.model_id or "").casefold()
            == str(device_to_find.model_id).casefold()
        )


class DeviceBatteryDetails(NamedTuple):
    """Describes a device battery type."""

    manufacturer: str
    model: str
    model_id: str
    hw_version: str
    battery_type: str
    battery_quantity: int

    @property
    def is_manual(self):
        """Return whether the device should be discovered or battery type suggested."""
        return self.battery_type.casefold() == "manual".casefold()

    @property
    def battery_type_and_quantity(self):
        """Return battery type with quantity prefix."""
        try:
            quantity = int(self.battery_quantity)
        except ValueError:
            quantity = 0

        if quantity > 1:
            batteries = str(quantity) + "× " + self.battery_type
        else:
            batteries = self.battery_type

        return batteries


class ModelInfo(NamedTuple):
    """Describes a device."""

    manufacturer: str
    model: str
    model_id: str | None
    hw_version: str | None

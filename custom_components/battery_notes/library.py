"""Battery Type library for battery_notes."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Final, NamedTuple, cast

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import STORAGE_DIR

from .coordinator import MY_KEY

_LOGGER = logging.getLogger(__name__)

LIBRARY_DEVICES: Final[str] = "devices"
LIBRARY_MANUFACTURER: Final[str] =  "manufacturer"
LIBRARY_MODEL: Final[str] =  "model"
LIBRARY_MODEL_MATCH_METHOD: Final[str] =  "model_match_method"
LIBRARY_MODEL_ID: Final[str] =  "model_id"
LIBRARY_HW_VERSION: Final[str] =  "hw_version"
LIBRARY_BATTERY_TYPE: Final[str] =  "battery_type"
LIBRARY_BATTERY_QUANTITY: Final[str] =  "battery_quantity"
LIBRARY_MISSING: Final[str] = "##MISSING##"


class Library:  # pylint: disable=too-few-public-methods
    """Hold all known battery types."""

    _devices: list = []

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
            json_user_path = self.hass.config.path(STORAGE_DIR, "battery_notes", domain_config.user_library)
            _LOGGER.debug("Using user library file at %s", json_user_path)

            try:
                user_json_data = await self.hass.async_add_executor_job(
                    _load_library_json, json_user_path
                )

                self._devices = user_json_data["devices"]
                _LOGGER.debug(
                    "Loaded %s user devices", len(user_json_data["devices"])
                )

            except FileNotFoundError:
                # Try to move the user library to new location
                try:
                    legacy_data_directory = os.path.join(os.path.dirname(__file__), "data")
                    legacy_json_user_path = os.path.join(legacy_data_directory, domain_config.user_library)
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
        json_default_path = self.hass.config.path(STORAGE_DIR, "battery_notes", "library.json")

        _LOGGER.debug("Using library file at %s", json_default_path)

        try:
            default_json_data = await self.hass.async_add_executor_job(
                _load_library_json, json_default_path
            )
            self._devices.extend(default_json_data[LIBRARY_DEVICES])
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

        if self._devices is None:
            return None

        # Test only
        # device_to_find = ModelInfo("Espressif", "m5stack-atom", None, None)

        # Get all devices matching manufacturer & model
        matching_devices = None
        partial_matching_devices = None
        fully_matching_devices = None

        matching_devices = [
            x for x in self._devices if self.device_basic_match(x, device_to_find)
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

        if not matching_devices or len(matching_devices) == 0:
            return None

        matched_device = matching_devices[0]
        return DeviceBatteryDetails(
            manufacturer=matched_device[LIBRARY_MANUFACTURER],
            model=matched_device[LIBRARY_MODEL],
            model_id=matched_device.get("model_id", ""),
            hw_version=matched_device.get(LIBRARY_HW_VERSION, ""),
            battery_type=matched_device[LIBRARY_BATTERY_TYPE],
            battery_quantity=matched_device.get(LIBRARY_BATTERY_QUANTITY, 1),
        )

    def loaded(self) -> bool:
        """Library loaded successfully."""
        return self._devices is not None

    def device_basic_match(self, device: dict[str, Any], model_info: ModelInfo) -> bool:
        """Check if device match on manufacturer and model."""
        if (
            str(device[LIBRARY_MANUFACTURER] or "").casefold()
            != str(model_info.manufacturer or "").casefold()
        ):
            return False

        if LIBRARY_MODEL_MATCH_METHOD in device:
            if device[LIBRARY_MODEL_MATCH_METHOD] == "startswith":
                if (
                    str(model_info.model or "")
                    .casefold()
                    .startswith(str(device[LIBRARY_MODEL] or "").casefold())
                ):
                    return True
            if device[LIBRARY_MODEL_MATCH_METHOD] == "endswith":
                if (
                    str(model_info.model or "")
                    .casefold()
                    .endswith(str(device[LIBRARY_MODEL] or "").casefold())
                ):
                    return True
            if device[LIBRARY_MODEL_MATCH_METHOD] == "contains":
                if str(model_info.model or "").casefold() in (
                    str(device[LIBRARY_MODEL] or "").casefold()
                ):
                    return True
        else:
            if (
                str(device[LIBRARY_MODEL] or "").casefold()
                == str(model_info.model or "").casefold()
            ):
                return True
        return False

    def device_partial_match(
        self, device: dict[str, Any], model_info: ModelInfo
    ) -> bool:
        """Check if device match on hw_version or model_id."""
        if model_info.hw_version is None or model_info.model_id is None:
            if (
                device.get(LIBRARY_HW_VERSION, LIBRARY_MISSING).casefold()
                == str(model_info.hw_version).casefold()
                and device.get(LIBRARY_MODEL_ID, LIBRARY_MISSING).casefold()
                == str(model_info.model_id).casefold()
            ):
                return True
        else:
            if (
                device.get(LIBRARY_HW_VERSION, LIBRARY_MISSING).casefold()
                == str(model_info.hw_version).casefold()
                or device.get(LIBRARY_MODEL_ID, LIBRARY_MISSING).casefold()
                == str(model_info.model_id).casefold()
            ):
                return True
        return False

    def device_full_match(self, device: dict[str, Any], model_info: ModelInfo) -> bool:
        """Check if device match on hw_version and model_id."""
        if (
            device.get(LIBRARY_HW_VERSION, LIBRARY_MISSING).casefold()
            == str(model_info.hw_version).casefold()
            and device.get(LIBRARY_MODEL_ID, LIBRARY_MISSING).casefold()
            == str(model_info.model_id).casefold()
        ):
            return True
        return False


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

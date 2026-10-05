"""Battery Type library for battery_notes."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, NamedTuple

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util.hass_dict import HassKey

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
        """Create LibraryDevice instance from JSON data.

        Raises ValueError for entries without the required fields or with wrong types.
        """
        if not isinstance(data, dict):
            raise ValueError(f"Device entry is not an object: {data!r}")

        for key in (LIBRARY_MANUFACTURER, LIBRARY_MODEL, LIBRARY_BATTERY_TYPE):
            if not isinstance(data.get(key), str) or not data[key]:
                raise ValueError(f"Device entry has no {key}: {data!r}")
        for key in (LIBRARY_MODEL_MATCH_METHOD, LIBRARY_MODEL_ID, LIBRARY_HW_VERSION):
            if data.get(key) is not None and not isinstance(data[key], str):
                raise ValueError(f"Device entry has an invalid {key}: {data!r}")

        battery_quantity = data.get(LIBRARY_BATTERY_QUANTITY, 1)
        if isinstance(battery_quantity, bool) or not isinstance(battery_quantity, int):
            raise ValueError(f"Device entry has an invalid battery quantity: {data!r}")

        return cls(
            manufacturer=data[LIBRARY_MANUFACTURER],
            model=data[LIBRARY_MODEL],
            model_match_method=data.get(LIBRARY_MODEL_MATCH_METHOD),
            model_id=data.get(LIBRARY_MODEL_ID),
            hw_version=data.get(LIBRARY_HW_VERSION),
            battery_type=data[LIBRARY_BATTERY_TYPE],
            battery_quantity=battery_quantity,
        )


def _parse_library(
    json_data: Any, library_file: str
) -> tuple[list[LibraryDevice], set[str]]:
    """Return the valid devices and the ignored domains of a library.

    Invalid device entries are skipped so one bad entry doesn't discard the library.
    """
    if not isinstance(json_data, dict) or not isinstance(
        json_data.get(LIBRARY_DEVICES), list
    ):
        raise ValueError("no devices list")

    devices: list[LibraryDevice] = []
    for json_device in json_data[LIBRARY_DEVICES]:
        try:
            devices.append(LibraryDevice.from_json(json_device))
        except ValueError as err:
            _LOGGER.warning("Skipping invalid device in %s: %s", library_file, err)
    _LOGGER.info("Loaded %s devices from %s", len(devices), library_file)

    ignored_domains: set[str] = set()
    if isinstance(json_data.get("ignored_domains"), list):
        ignored_domains = {
            str(domain).casefold() for domain in json_data["ignored_domains"]
        }
        _LOGGER.info(
            "Loaded %s ignored domains from %s", len(ignored_domains), library_file
        )

    return devices, ignored_domains


class Library:  # pylint: disable=too-few-public-methods
    """Hold all known battery types."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Init."""
        self.hass = hass
        self._manufacturer_devices: dict[str, list[LibraryDevice]] = {}
        self._ignored_domains: set[str] = set()
        self._load_lock = asyncio.Lock()

    async def load_libraries(self):
        """Load the user and default libraries."""
        async with self._load_lock:
            await self._do_load_libraries()

    async def _do_load_libraries(self) -> None:
        """Load libraries internally (must be called with lock held)."""

        def _load_library_json(
            library_file: str, legacy_library_file: str | None = None
        ) -> Any:
            """Load a library json file, moving it from the legacy location if needed."""
            if (
                legacy_library_file
                and not Path(library_file).exists()
                and Path(legacy_library_file).exists()
            ):
                os.makedirs(os.path.dirname(library_file), exist_ok=True)
                os.rename(legacy_library_file, library_file)
                _LOGGER.debug("User library moved to %s", library_file)

            with open(library_file, encoding="utf-8") as file:
                return json.load(file)

        new_manufacturer_devices: dict[str, list[LibraryDevice]] = {}
        new_ignored_domains: set[str] = set()
        library_files: list[tuple[str, str | None]] = []

        # User Library, searched before the default library
        domain_config = self.hass.data.get(MY_KEY)
        if domain_config and domain_config.user_library != "":
            library_files.append(
                (
                    self.hass.config.path(
                        STORAGE_DIR, "battery_notes", domain_config.user_library
                    ),
                    os.path.join(
                        os.path.dirname(__file__), "data", domain_config.user_library
                    ),
                )
            )

        # Default Library
        library_files.append(
            (self.hass.config.path(STORAGE_DIR, "battery_notes", "library.json"), None)
        )

        for library_file, legacy_library_file in library_files:
            try:
                json_data = await self.hass.async_add_executor_job(
                    _load_library_json, library_file, legacy_library_file
                )
                devices, ignored_domains = _parse_library(json_data, library_file)
            except FileNotFoundError:
                _LOGGER.error("Library file not found at %s", library_file)
                continue
            except (OSError, ValueError) as err:
                _LOGGER.error("Failed to load library file %s: %s", library_file, err)
                continue

            for library_device in devices:
                new_manufacturer_devices.setdefault(
                    library_device.manufacturer.casefold(), []
                ).append(library_device)
            new_ignored_domains.update(ignored_domains)

        # Keep the previously loaded library if nothing could be loaded this time
        if new_manufacturer_devices:
            self._manufacturer_devices = new_manufacturer_devices
            self._ignored_domains = new_ignored_domains

    def is_domain_ignored(self, domain: str) -> bool:
        """Check if an integration domain is ignored."""
        return domain.casefold() in self._ignored_domains

    async def get_device_battery_details(  # noqa: PLR0911, PLR0912
        self,
        device_to_find: ModelInfo,
    ) -> DeviceBatteryDetails | None:
        """Create a battery details object from the JSON devices data."""

        if not bool(self._manufacturer_devices):
            return None

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

        if not matching_devices:
            return None

        # If search doesn't specify model_id/hw_version, filter to entries without them
        if device_to_find.model_id is None and device_to_find.hw_version is None:
            generic_matches = [
                x
                for x in matching_devices
                if x.model_id is None and x.hw_version is None
            ]
            if generic_matches:
                matching_devices = generic_matches
            else:
                # No generic version found when searching without specifics
                return None

        # If a search contains specific identifiers, reject entries that are
        # incompatible with those constraints. Generic entries (without
        # identifiers) can still be used as fallback matches.
        if device_to_find.model_id is not None or device_to_find.hw_version is not None:
            matching_devices = [
                x
                for x in matching_devices
                if not (device_to_find.model_id is None and x.model_id is not None)
                and not (device_to_find.hw_version is None and x.hw_version is not None)
                and not (
                    device_to_find.model_id is not None
                    and x.model_id is not None
                    and x.model_id.casefold() != device_to_find.model_id.casefold()
                )
                and not (
                    device_to_find.hw_version is not None
                    and x.hw_version is not None
                    and x.hw_version.casefold() != device_to_find.hw_version.casefold()
                )
            ]
            if not matching_devices:
                return None

        # Narrow down from multiple matches
        if matching_devices and len(matching_devices) > 1:
            partial_matching_devices = [
                x
                for x in matching_devices
                if self.device_partial_match(x, device_to_find)
            ]

            if partial_matching_devices:
                matching_devices = partial_matching_devices

                # Only try full match if we still have multiple matches
                if len(matching_devices) > 1:
                    fully_matching_devices = [
                        x
                        for x in matching_devices
                        if self.device_full_match(x, device_to_find)
                    ]
                    if fully_matching_devices:
                        matching_devices = fully_matching_devices

        if not matching_devices:
            return None

        first_matched_device = matching_devices[0]

        if len(matching_devices) > 1:
            # Check if all matching devices are duplicates (all fields identical)
            all_same = all(
                device.manufacturer == first_matched_device.manufacturer
                and device.model == first_matched_device.model
                and device.model_id == first_matched_device.model_id
                and device.hw_version == first_matched_device.hw_version
                and device.model_match_method == first_matched_device.model_match_method
                and device.battery_type == first_matched_device.battery_type
                and device.battery_quantity == first_matched_device.battery_quantity
                for device in matching_devices[1:]
            )
            if not all_same:
                return None

        return DeviceBatteryDetails(
            manufacturer=first_matched_device.manufacturer,
            model=first_matched_device.model,
            model_id=first_matched_device.model_id or "",
            hw_version=first_matched_device.hw_version or "",
            battery_type=first_matched_device.battery_type,
            battery_quantity=first_matched_device.battery_quantity,
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
                if library_device.model.casefold() in (
                    str(device_to_find.model or "").casefold()
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

        # Only compare fields that exist in device_to_find
        if (
            device_to_find.hw_version is not None
            and device_to_find.model_id is not None
        ):
            if (
                library_device.hw_version or ""
            ).casefold() == device_to_find.hw_version.casefold() and (
                library_device.model_id or ""
            ).casefold() == device_to_find.model_id.casefold():
                return True

        if device_to_find.hw_version is not None:
            if (
                library_device.hw_version or ""
            ).casefold() == device_to_find.hw_version.casefold():
                return True

        if device_to_find.model_id is not None:
            if (
                library_device.model_id or ""
            ).casefold() == device_to_find.model_id.casefold():
                return True

        return False

    def device_full_match(
        self, library_device: LibraryDevice, device_to_find: ModelInfo
    ) -> bool:
        """Check if device match on hw_version and model_id."""
        return bool(
            (library_device.hw_version or "").casefold()
            == (device_to_find.hw_version or "").casefold()
            and (library_device.model_id or "").casefold()
            == (device_to_find.model_id or "").casefold()
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

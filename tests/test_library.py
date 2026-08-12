"""Tests for library matching logic."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from custom_components.battery_notes.library import (
    Library,
    LibraryDevice,
    ModelInfo,
)


@pytest.fixture
def library_with_data() -> Library:
    """Load library from the actual library.json file."""
    # Create mock hass
    hass_mock = MagicMock()
    hass_mock.data = {}

    library = Library(hass_mock)

    # Load the actual library.json file
    library_path = Path(__file__).parent.parent / "library" / "library.json"
    with open(library_path, encoding="utf-8") as file:
        library_data = json.load(file)

    # Populate the library from the JSON data
    for device_data in library_data["devices"]:
        library_device = LibraryDevice.from_json(device_data)
        manufacturer = library_device.manufacturer.casefold()
        if manufacturer not in library._manufacturer_devices:  # noqa: SLF001
            library._manufacturer_devices[manufacturer] = []  # noqa: SLF001
        library._manufacturer_devices[manufacturer].append(library_device)  # noqa: SLF001

    return library


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("manufacturer", "model", "model_id", "hw_version", "expected_battery"),
    [
        # No match as lib does not have only manufacturer and model entry
        pytest.param(
            "Aqara",
            "Roller shade driver E1",
            None,
            None,
            None,
            id="aqara_with_model_libary_more_specific",
        ),
        # Match with no model_id or hw_version in lib, model_id on device
        pytest.param(
            "eQ-3",
            "HmIP-SRH",
            "Homematic IP Fenster-/ Drehgriffkontakt",
            None,
            "AAA",
            id="eq3_hmip_srh_no_model",
        ),
        # Match with no model_id or hw_version in lib, hw_version on device
        pytest.param(
            "eQ-3",
            "HmIP-WGC",
            None,
            "HW Version",
            "2× AA",
            id="eq3_hmip_srh_no_hw_version",
        ),
        # Match with model_id but no hw_version
        pytest.param(
            "Aqara",
            "Roller shade driver E1",
            "ZNJLBL01LM",
            None,
            "Rechargeable",
            id="aqara_with_model_id",
        ),
        # Match with hw_version but no model_id
        pytest.param(
            "Google",
            "Topaz-2.7",
            None,
            "Battery",
            "6× AA",
            id="google_battery_variant",
        ),
        # Match with hw_version but no model_id
        pytest.param(
            "Google",
            "Topaz-2.7",
            None,
            "Wired",
            "3× AA",
            id="google_wired_variant",
        ),
        # Match with no model_id or hw_version
        pytest.param(
            "LUMI",
            "lumi.sensor_magnet.aq2",
            None,
            None,
            "CR1632",
            id="lumi_basic_match",
        ),
        # No match with no model_id or hw_version
        pytest.param(
            "SOMFY",
            "RollerShutter",
            None,
            None,
            None,
            id="somfy_no_match",
        ),
        # No match
        pytest.param(
            "Unknown",
            "Unknown Device",
            None,
            None,
            None,
            id="unknown_device",
        ),
    ],
)
async def test_get_device_battery_details(  # noqa: PLR0913
    library_with_data: Library,
    manufacturer: str,
    model: str,
    model_id: str | None,
    hw_version: str | None,
    expected_battery: str | None,
) -> None:
    """Test device battery details lookup with various scenarios."""
    device_to_find = ModelInfo(
        manufacturer=manufacturer,
        model=model,
        model_id=model_id,
        hw_version=hw_version,
    )

    result = await library_with_data.get_device_battery_details(device_to_find)

    if expected_battery is None:
        assert result is None
    else:
        assert result is not None
        assert result.battery_type_and_quantity == expected_battery

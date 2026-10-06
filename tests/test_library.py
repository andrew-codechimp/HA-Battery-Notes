"""Tests for library loading and matching rules."""

import json
from unittest.mock import MagicMock, mock_open

import pytest
from custom_components.battery_notes.library import Library, ModelInfo


@pytest.mark.parametrize(
    ("model_info", "expected_battery"),
    [
        pytest.param(ModelInfo("Mi", "MS009", None, None), "CR2540", id="model-only"),
        pytest.param(
            ModelInfo(
                "eQ-3", "HmIP-SRH", "Homematic IP Fenster-/ Drehgriffkontakt", None
            ),
            "AAA",
            id="model-id",
        ),
        pytest.param(
            ModelInfo("eQ-3", "HmIP-WGC", None, "HW Version"),
            "2× AA",
            id="generic-hardware-fallback",
        ),
        pytest.param(
            ModelInfo("Aqara", "Roller shade driver E1", "ZNJLBL01LM", None),
            "Rechargeable",
            id="specific-model-id",
        ),
        pytest.param(
            ModelInfo("Google", "Topaz-2.7", None, "Battery"),
            "6× AA",
            id="battery-variant",
        ),
        pytest.param(
            ModelInfo("Google", "Topaz-2.7", None, "Wired"), "3× AA", id="wired-variant"
        ),
        pytest.param(
            ModelInfo("LUMI", "lumi.sensor_magnet.aq2", None, None),
            "CR1632",
            id="generic-model",
        ),
        pytest.param(
            ModelInfo("lumi", "LUMI.SENSOR_MAGNET.AQ2", None, None),
            "CR1632",
            id="case-insensitive",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Specific sensor", None, None),
            "AA",
            id="generic-preferred-without-identifiers",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Specific sensor", "unknown", None),
            "AA",
            id="generic-model-id-fallback",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Specific sensor", "S1", None),
            "2× AAA",
            id="partial-match-preferred",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Specific sensor", "s1", "rev2"),
            "4× CR2032",
            id="full-match-preferred",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Duplicate sensor", None, None),
            "CR2032",
            id="identical-duplicates",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Manual sensor", None, None),
            "Manual",
            id="manual-definition",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Prefix sensor", None, None),
            "AA",
            id="startswith",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Sensor Suffix", None, None),
            "AAA",
            id="endswith",
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Sensor Middle variant", None, None),
            "CR2032",
            id="contains",
        ),
    ],
)
async def test_get_device_battery_details(
    loaded_library: Library, model_info: ModelInfo, expected_battery: str
) -> None:
    """Test exact, fallback, and partial model matches using a loaded library."""
    result = await loaded_library.get_device_battery_details(model_info)

    assert result is not None
    assert result.battery_type_and_quantity == expected_battery


@pytest.mark.parametrize(
    "model_info",
    [
        pytest.param(
            ModelInfo("Aqara", "Roller shade driver E1", None, None),
            id="missing-required-model-id",
        ),
        pytest.param(
            ModelInfo("Meross", "Smart Presence Sensor", "NONEXISTENT_MODEL_ID", None),
            id="wrong-model-id",
        ),
        pytest.param(
            ModelInfo(
                "Meross", "Smart Presence Sensor", None, "NONEXISTENT_HW_VERSION"
            ),
            id="missing-model-id-with-hardware",
        ),
        pytest.param(
            ModelInfo(
                "Meross",
                "Smart Presence Sensor",
                "NONEXISTENT_MODEL_ID",
                "NONEXISTENT_HW_VERSION",
            ),
            id="wrong-identifiers",
        ),
        pytest.param(
            ModelInfo("Mi", "NONEXISTENT_MODEL", None, None), id="unknown-model"
        ),
        pytest.param(
            ModelInfo("SOMFY", "RollerShutter", None, None),
            id="unsupported-manufacturer",
        ),
        pytest.param(
            ModelInfo("Unknown", "Unknown Device", None, None), id="unknown-device"
        ),
        pytest.param(
            ModelInfo("Google", "Topaz-2.7", None, "Unknown"), id="wrong-hardware"
        ),
        pytest.param(
            ModelInfo("Test Manufacturer", "Ambiguous sensor", None, None),
            id="conflicting-matches",
        ),
    ],
)
async def test_no_matching_device(
    loaded_library: Library, model_info: ModelInfo
) -> None:
    """Test absent, incompatible, and ambiguous matches return no battery details."""
    assert await loaded_library.get_device_battery_details(model_info) is None


async def test_unloaded_library(battery_library: Library) -> None:
    """Test lookups return no match before the library is loaded."""
    assert not battery_library.is_loaded
    assert (
        await battery_library.get_device_battery_details(
            ModelInfo("LUMI", "lumi.sensor_magnet.aq2", None, None)
        )
        is None
    )


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        pytest.param("unifi", True, id="ignored"),
        pytest.param("UNIFI", True, id="ignored-case-insensitive"),
        pytest.param("mqtt", False, id="allowed"),
    ],
)
async def test_ignored_domains(
    loaded_library: Library, domain: str, expected: bool
) -> None:
    """Test the normal loader applies the fixture's ignored integration domains."""
    assert loaded_library.is_domain_ignored(domain) is expected


@pytest.fixture
def library_with_invalid_entries(_mock_library_file: MagicMock) -> None:
    """Provide a library mixing valid and invalid device entries."""
    _mock_library_file.return_value = mock_open(
        read_data=json.dumps(
            {
                "version": 1,
                "ignored_domains": ["unifi"],
                "devices": [
                    {"manufacturer": "Mi", "model": "MS009", "battery_type": "CR2540"},
                    {"manufacturer": "Mi", "model": "No battery type"},
                    {"manufacturer": None, "model": "X", "battery_type": "AA"},
                    {
                        "manufacturer": "Mi",
                        "model": "X",
                        "battery_type": "AA",
                        "model_id": 1,
                    },
                    {
                        "manufacturer": "Mi",
                        "model": "Y",
                        "battery_type": "AA",
                        "battery_quantity": "2",
                    },
                    "not a device",
                ],
            }
        )
    ).return_value


@pytest.mark.usefixtures("library_with_invalid_entries")
async def test_invalid_entries_skipped(
    battery_library: Library, caplog: pytest.LogCaptureFixture
) -> None:
    """Test invalid device entries are skipped without discarding the library."""
    await battery_library.load_libraries()

    assert battery_library.is_loaded
    assert battery_library.is_domain_ignored("unifi")
    details = await battery_library.get_device_battery_details(
        ModelInfo("Mi", "MS009", None, None)
    )
    assert details is not None
    assert details.battery_type == "CR2540"
    assert caplog.text.count("Skipping invalid device") == 5

"""Tests for linking Battery Notes to battery percentage sensors."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from custom_components.battery_notes.coordinator import BatteryNotesSubentryCoordinator

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT, PERCENTAGE
from homeassistant.core import State
from homeassistant.helpers.entity_registry import RegistryEntry


@pytest.mark.parametrize("association", ["entity", "device"])
@pytest.mark.parametrize(
    ("registry_unit", "live_unit", "state_present", "expected_match"),
    [
        (None, PERCENTAGE, True, True),
        (PERCENTAGE, None, False, True),
        (PERCENTAGE, PERCENTAGE, True, True),
        (None, None, False, False),
        (None, None, True, False),
        (None, "V", True, False),
        ("V", PERCENTAGE, True, False),
    ],
)
def test_link_battery_percentage_sensor(
    association: str,
    registry_unit: str | None,
    live_unit: str | None,
    state_present: bool,
    expected_match: bool,
) -> None:
    """Use a live percentage unit only when the registry unit is missing."""
    entity = MagicMock(
        spec=RegistryEntry,
        entity_id="sensor.test_battery",
        domain="sensor",
        platform="test",
        device_class=None,
        original_device_class=SensorDeviceClass.BATTERY,
        unit_of_measurement=registry_unit,
    )
    coordinator = BatteryNotesSubentryCoordinator.__new__(
        BatteryNotesSubentryCoordinator
    )
    coordinator.hass = MagicMock()
    coordinator.device_id = "test-device" if association == "device" else None
    coordinator.source_entity_id = entity.entity_id if association == "entity" else None
    coordinator.subentry = MagicMock(title="Test device")
    coordinator.hass.states.get.return_value = (
        State(
            entity.entity_id,
            "84",
            {ATTR_UNIT_OF_MEASUREMENT: live_unit} if live_unit is not None else {},
        )
        if state_present
        else None
    )
    registry = MagicMock()
    registry.async_get.return_value = entity
    registry.entities.get_entries_for_device_id.return_value = [entity]

    with (
        patch(
            "custom_components.battery_notes.coordinator.er.async_get",
            return_value=registry,
        ),
        patch("custom_components.battery_notes.coordinator.dr.async_get"),
    ):
        assert coordinator._link_to_source()  # noqa: SLF001

    assert coordinator.wrapped_battery == (entity if expected_match else None)

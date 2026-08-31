"""Tests for BatteryNotesBatteryBinaryLowSensor's coordinator-refresh handling.

`battery_low_binary_state` is a bool (see `async_state_changed_listener`,
which assigns it `wrapped_battery_low_state.state == "on"` once). Comparing
it against the string "on" again in `_handle_coordinator_update` is always
False, which is why a coordinator refresh (e.g. HA startup/reload) always
reset the exposed entity to "off" regardless of the real source state --
only a live state-change event (which sets `_attr_is_on` directly from the
bool) ever showed the correct value. See issue #5078.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from custom_components.battery_notes.binary_sensor import (
    BatteryNotesBatteryBinaryLowSensor,
)

from homeassistant.const import STATE_UNAVAILABLE


def _sensor(
    *, battery_low_binary_state: bool, wrapped_state: str
) -> BatteryNotesBatteryBinaryLowSensor:
    """Build a BatteryNotesBatteryBinaryLowSensor with just enough wiring for _handle_coordinator_update."""
    sensor = BatteryNotesBatteryBinaryLowSensor.__new__(
        BatteryNotesBatteryBinaryLowSensor
    )

    sensor.coordinator = MagicMock()
    sensor.coordinator.wrapped_battery_low = MagicMock(
        entity_id="binary_sensor.source_battery"
    )
    sensor.coordinator.battery_low_binary_state = battery_low_binary_state

    sensor.hass = MagicMock()
    sensor.hass.states.get.return_value = MagicMock(state=wrapped_state)

    sensor.async_write_ha_state = MagicMock()

    return sensor


@pytest.mark.parametrize(
    ("battery_low_binary_state", "expected_is_on"),
    [
        (True, True),
        (False, False),
    ],
)
def test_handle_coordinator_update_reflects_stored_bool(
    battery_low_binary_state: bool, expected_is_on: bool
) -> None:
    """A coordinator refresh must expose the stored bool as-is."""
    sensor = _sensor(
        battery_low_binary_state=battery_low_binary_state, wrapped_state="on"
    )

    sensor._handle_coordinator_update()  # noqa: SLF001

    assert sensor._attr_is_on is expected_is_on  # noqa: SLF001


def test_handle_coordinator_update_matches_state_changed_listener() -> None:
    """The two update paths must agree.

    A source already 'on' at coordinator refresh time (e.g. HA startup)
    must expose the same state a live state-change event would have set.
    """
    sensor = _sensor(battery_low_binary_state=True, wrapped_state="on")

    sensor._handle_coordinator_update()  # noqa: SLF001

    assert sensor._attr_is_on is True  # noqa: SLF001


def test_handle_coordinator_update_unavailable_source() -> None:
    """An unavailable/unknown source clears the state, regardless of the stored bool."""
    sensor = _sensor(battery_low_binary_state=True, wrapped_state=STATE_UNAVAILABLE)

    sensor._handle_coordinator_update()  # noqa: SLF001

    assert sensor._attr_is_on is None  # noqa: SLF001
    assert sensor._attr_available is False  # noqa: SLF001

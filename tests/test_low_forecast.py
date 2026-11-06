"""Tests for the Battery Notes low forecast sensor."""

from datetime import UTC, datetime, timedelta

import pytest
from custom_components.battery_notes.const import (
    ATTR_BATTERY_DRAIN_RATE,
    ATTR_BATTERY_DRAIN_SPAN_DAYS,
    ATTR_BATTERY_LEVEL_JUMPS,
    DOMAIN,
)
from custom_components.battery_notes.sensor import LOW_FORECAST_REFRESH_INTERVAL
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.const import ATTR_ENTITY_ID, PERCENTAGE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

SOURCE_ENTITY_ID = "sensor.door_battery"
PAIRED = datetime(2026, 1, 1, 12, tzinfo=UTC)
NOW = PAIRED + timedelta(days=61)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    recorder_mock: Recorder,
    enable_custom_integrations: None,
) -> None:
    """Start the recorder before hass, which conftest's version would set up first."""


@pytest.fixture(autouse=True)
def freeze_pairing_time(freezer: FrozenDateTimeFactory) -> None:
    """Create the source device, and so its default replacement date, at PAIRED."""
    freezer.move_to(PAIRED)


def _entity_id(hass: HomeAssistant, platform: str, suffix: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"bn_door_battery{suffix}"
    )
    assert entity_id is not None
    return entity_id


async def _import_history(hass: HomeAssistant) -> None:
    """Record a battery losing 0.5% a day for the 60 days after pairing."""
    async_import_statistics(
        hass,
        {
            "mean_type": StatisticMeanType.ARITHMETIC,
            "has_sum": False,
            "name": None,
            "source": "recorder",
            "statistic_id": SOURCE_ENTITY_ID,
            "unit_class": None,
            "unit_of_measurement": PERCENTAGE,
        },
        [
            {
                "start": PAIRED + timedelta(days=day),
                "mean": 100 - 0.5 * day,
                "min": 100 - 0.5 * day,
                "max": 100 - 0.5 * day,
            }
            for day in range(1, 61)
        ],
    )
    await async_wait_recording_done(hass)


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_low_forecast(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Forecast from statistics, follow the level, and reset on replacement."""
    await _import_history(hass)

    freezer.move_to(NOW)
    await setup_integration(hass, battery_note_config_entry)
    entity_id = _entity_id(hass, "sensor", "_battery_low_forecast")

    # Source reports 55%, default low threshold is 10%: 45 / 0.5 = 90 days
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == (NOW + timedelta(days=90)).isoformat()
    assert state.attributes[ATTR_BATTERY_DRAIN_RATE] == 0.5
    assert state.attributes[ATTR_BATTERY_DRAIN_SPAN_DAYS] >= 30
    assert state.attributes[ATTR_BATTERY_LEVEL_JUMPS] == 0

    # A new reading moves the forecast without re-querying
    hass.states.async_set(
        SOURCE_ENTITY_ID, "45", hass.states.get(SOURCE_ENTITY_ID).attributes
    )
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == (NOW + timedelta(days=70)).isoformat()

    # Replacing the battery discards the old battery's history
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: _entity_id(hass, "button", "_battery_replaced_button")},
        blocking=True,
    )
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNKNOWN


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_low_forecast_follows_source_rename(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """After the source entity ID changes, refreshes query the new ID."""
    await _import_history(hass)
    freezer.move_to(NOW)
    await setup_integration(hass, battery_note_config_entry)
    entity_id = _entity_id(hass, "sensor", "_battery_low_forecast")
    attributes = hass.states.get(SOURCE_ENTITY_ID).attributes

    er.async_get(hass).async_update_entity(
        SOURCE_ENTITY_ID, new_entity_id="sensor.door_battery_renamed"
    )
    hass.states.async_set("sensor.door_battery_renamed", "55", attributes)
    await hass.async_block_till_done()
    await async_wait_recording_done(hass)

    freezer.tick(LOW_FORECAST_REFRESH_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get(entity_id)
    assert state is not None
    assert (
        state.state
        == (NOW + LOW_FORECAST_REFRESH_INTERVAL + timedelta(days=90)).isoformat()
    )

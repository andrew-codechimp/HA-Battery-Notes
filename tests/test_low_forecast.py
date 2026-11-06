"""Tests for the Battery Notes low forecast sensor."""

from collections.abc import Callable, Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

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
from sqlalchemy.exc import OperationalError

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")

SOURCE_ENTITY_ID = "sensor.door_battery"
PAIRED = datetime(2026, 1, 1, 12, tzinfo=UTC)
NOW = PAIRED + timedelta(days=61)

# A battery losing 0.5% a day for the 60 days after pairing
HISTORY = [
    {"start": (PAIRED + timedelta(days=day)).timestamp(), "mean": 100 - 0.5 * day}
    for day in range(1, 61)
]


@pytest.fixture(autouse=True)
def freeze_pairing_time(freezer: FrozenDateTimeFactory) -> None:
    """Create the source device, and so its default replacement date, at PAIRED."""
    freezer.move_to(PAIRED)


@pytest.fixture
def statistics(hass: HomeAssistant) -> Generator[MagicMock]:
    """Serve HISTORY for whichever statistic ID is queried.

    The pinned test plugin's recorder fixture fails on Python 3.14, so the
    recorder boundary is stubbed instead.
    """

    def _during_period(
        _hass: HomeAssistant, _start: datetime, _end: None, ids: set[str], *_: Any
    ) -> dict[str, list[dict[str, float]]]:
        return dict.fromkeys(ids, HISTORY)

    async def _run(func: Callable[..., Any], *args: Any) -> Any:
        return func(*args)

    hass.config.components.add("recorder")
    query = MagicMock(side_effect=_during_period)
    instance = MagicMock(async_add_executor_job=AsyncMock(side_effect=_run))
    with (
        patch(
            "custom_components.battery_notes.sensor.get_instance",
            return_value=instance,
        ),
        patch("custom_components.battery_notes.sensor.statistics_during_period", query),
    ):
        yield query


def _entity_id(hass: HomeAssistant, platform: str, suffix: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        platform, DOMAIN, f"bn_door_battery{suffix}"
    )
    assert entity_id is not None
    return entity_id


async def _setup_at_now(
    hass: HomeAssistant, entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> str:
    freezer.move_to(NOW)
    await setup_integration(hass, entry)
    return _entity_id(hass, "sensor", "_battery_low_forecast")


async def _refresh(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    freezer.tick(LOW_FORECAST_REFRESH_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_low_forecast(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    statistics: MagicMock,
) -> None:
    """Forecast from statistics, follow the level, and reset on replacement."""
    entity_id = await _setup_at_now(hass, battery_note_config_entry, freezer)

    statistics.assert_called_once()
    assert statistics.call_args.args[3] == {SOURCE_ENTITY_ID}
    assert statistics.call_args.args[4] == "day"

    # Source reports 55%, default low threshold is 10%: 45 / 0.5 = 90 days
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == (NOW + timedelta(days=90)).isoformat()
    assert state.attributes[ATTR_BATTERY_DRAIN_RATE] == 0.5
    assert state.attributes[ATTR_BATTERY_DRAIN_SPAN_DAYS] == 59
    assert state.attributes[ATTR_BATTERY_LEVEL_JUMPS] == 0

    # A new reading moves the forecast without re-querying
    source = hass.states.get(SOURCE_ENTITY_ID)
    assert source is not None
    hass.states.async_set(SOURCE_ENTITY_ID, "45", source.attributes)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == (NOW + timedelta(days=70)).isoformat()
    statistics.assert_called_once()

    # Replacing the battery re-fits from the replacement, discarding history
    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {ATTR_ENTITY_ID: _entity_id(hass, "button", "_battery_replaced_button")},
        blocking=True,
    )
    freezer.tick(timedelta(seconds=11))  # Past the coordinator's refresh debounce
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert statistics.call_count == 2
    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == STATE_UNKNOWN


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_low_forecast_follows_source_rename(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    statistics: MagicMock,
) -> None:
    """After the source entity ID changes, refreshes query the new ID."""
    entity_id = await _setup_at_now(hass, battery_note_config_entry, freezer)
    source = hass.states.get(SOURCE_ENTITY_ID)
    assert source is not None

    er.async_get(hass).async_update_entity(
        SOURCE_ENTITY_ID, new_entity_id="sensor.door_battery_renamed"
    )
    hass.states.async_set("sensor.door_battery_renamed", "55", source.attributes)
    await hass.async_block_till_done()
    await _refresh(hass, freezer)

    assert statistics.call_args.args[3] == {"sensor.door_battery_renamed"}
    state = hass.states.get(entity_id)
    assert state is not None
    assert (
        state.state
        == (NOW + LOW_FORECAST_REFRESH_INTERVAL + timedelta(days=90)).isoformat()
    )


@pytest.mark.parametrize("battery_note_source", [pytest.param("device", id="device")])
async def test_low_forecast_keeps_value_on_database_error(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
    statistics: MagicMock,
) -> None:
    """A failed query keeps the last forecast instead of raising."""
    entity_id = await _setup_at_now(hass, battery_note_config_entry, freezer)
    state = hass.states.get(entity_id)
    assert state is not None
    before = state.state

    statistics.side_effect = OperationalError("SELECT", {}, Exception("locked"))
    await _refresh(hass, freezer)

    state = hass.states.get(entity_id)
    assert state is not None
    assert state.state == before

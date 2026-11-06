"""Test the battery drain-rate estimate."""

from datetime import UTC, datetime, timedelta

import pytest
from custom_components.battery_notes.drain import (
    SECONDS_PER_DAY,
    DrainEstimate,
    estimate_drain,
)

NOW = datetime(2026, 11, 1, tzinfo=UTC)
NOW_TS = NOW.timestamp()


def _daily(levels: list[float]) -> list[tuple[float, float]]:
    """Return daily points ending at NOW, oldest first."""
    start = NOW.timestamp() - (len(levels) - 1) * SECONDS_PER_DAY
    return [(start + i * SECONDS_PER_DAY, level) for i, level in enumerate(levels)]


def test_steady_drain() -> None:
    """A steady 0.5%/day discharge is fitted over the newest 60 days."""
    estimate = estimate_drain(_daily([100 - 0.5 * day for day in range(90)]), NOW_TS)

    assert estimate == DrainEstimate(rate=0.5, span_days=60, level_jumps=0)
    assert estimate.is_known
    # 55.5% now, 10% low threshold -> 91 days left
    assert estimate.low_at(55.5, 10, NOW) == NOW + timedelta(days=91)


def test_fit_starts_at_swap() -> None:
    """A level jump starts a new battery, the old one is ignored."""
    old = [80 - 1.0 * day for day in range(40)]
    new = [100 - 0.25 * day for day in range(40)]
    estimate = estimate_drain(_daily(old + new), NOW_TS)

    assert estimate is not None
    assert estimate.rate == 0.25
    assert estimate.span_days == 39
    assert estimate.level_jumps == 1


def test_fit_starts_at_last_replaced() -> None:
    """The recorded replacement wins over the 60 day window."""
    points = _daily([100 - 0.5 * day for day in range(90)])
    replaced = points[-20][0]

    estimate = estimate_drain(points, NOW_TS, replaced)

    assert estimate is not None
    assert estimate.span_days == 19
    assert not estimate.is_known  # too little history since replacement
    assert estimate.low_at(50, 10, NOW) is None


@pytest.mark.parametrize(
    "levels",
    [
        pytest.param([100.0] * 90, id="flat"),
        pytest.param([50 + 0.1 * day for day in range(90)], id="rising"),
        pytest.param([100 - 0.5 * day for day in range(20)], id="short history"),
    ],
)
def test_unknown_estimates(levels: list[float]) -> None:
    """Flat, rising or short histories give no forecast."""
    estimate = estimate_drain(_daily(levels), NOW_TS)

    assert estimate is not None
    assert not estimate.is_known


def test_repeated_jumps_flag_unstable() -> None:
    """Three or more jumps mean bad contacts or a failing cell."""
    levels = [60, 80, 60, 80, 60, 80] + [80 - 0.5 * day for day in range(40)]
    estimate = estimate_drain(_daily(levels), NOW_TS)

    assert estimate is not None
    assert estimate.level_jumps == 3
    assert estimate.is_unstable
    assert not estimate.is_known


def test_swap_across_two_days() -> None:
    """Rises split over consecutive days count as one jump at the run's end."""
    levels = [30.0] * 10 + [41.2, 55.1] + [55 - 0.5 * day for day in range(40)]
    points = _daily(levels)
    estimate = estimate_drain(points, NOW_TS)

    assert estimate is not None
    assert estimate.level_jumps == 1
    assert estimate.span_days == 40  # fitted from the 55.1 day onwards
    assert estimate.is_known


def test_silent_source_ages_out() -> None:
    """A source that stopped reporting 40 days ago has too little recent data."""
    points = _daily([100 - 1.0 * day for day in range(80)])
    stale = [(ts - 40 * SECONDS_PER_DAY, level) for ts, level in points]

    estimate = estimate_drain(stale, NOW_TS)

    assert estimate is not None
    assert estimate.span_days == 20  # only days 60..40 ago are in the window
    assert not estimate.is_known


def test_already_below_threshold() -> None:
    """A battery already under the threshold is due now."""
    estimate = DrainEstimate(rate=0.5, span_days=60, level_jumps=0)

    assert estimate.low_at(5, 10, NOW) == NOW


@pytest.mark.parametrize(
    "points", [pytest.param([], id="empty"), pytest.param(_daily([50]), id="one")]
)
def test_not_enough_points(points: list[tuple[float, float]]) -> None:
    """Fewer than two points cannot be fitted."""
    assert estimate_drain(points, NOW_TS) is None

"""Battery drain-rate estimation from daily long-term statistics."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise

HISTORY_DAYS = 120  # Daily means fetched; also the window for counting level jumps
FIT_DAYS = 60  # Newest data fitted, so old discharge behaviour stops dominating
MIN_SPAN_DAYS = 30  # Below this a slow cell's slope is indistinguishable from noise
MIN_RATE = 0.02  # %/day; slower than this means more than ~13 years per 100%
JUMP_PERCENT = 15  # A daily rise this big is a battery swap or a bad contact
UNSTABLE_JUMPS = 3  # This many rises within HISTORY_DAYS flags the cell/contacts

SECONDS_PER_DAY = 86400


@dataclass(frozen=True)
class DrainEstimate:
    """Result of fitting a battery's recent discharge."""

    rate: float  # % per day, positive while discharging
    span_days: int  # Days covered by the fitted points
    level_jumps: int  # Rises of JUMP_PERCENT or more within HISTORY_DAYS

    @property
    def is_unstable(self) -> bool:
        """Return True when repeated jumps make the slope meaningless."""
        return self.level_jumps >= UNSTABLE_JUMPS

    @property
    def is_known(self) -> bool:
        """Return True when the slope is trustworthy enough to predict from."""
        return (
            not self.is_unstable
            and self.span_days >= MIN_SPAN_DAYS
            and self.rate >= MIN_RATE
        )

    def low_at(
        self, level: float, low_threshold: float, now: datetime
    ) -> datetime | None:
        """Return when the battery is expected to reach the low threshold."""
        if not self.is_known or not math.isfinite(level):
            return None
        # Clamp so a garbage reading can't overflow timedelta
        headroom = min(max(level - low_threshold, 0.0), 100.0)
        return now + timedelta(days=headroom / self.rate)


def _level_jumps(points: list[tuple[float, float]]) -> list[float]:
    """Return timestamps where consecutive daily rises add up to JUMP_PERCENT.

    Summing the run catches a swap that straddles two daily buckets.
    """
    jumps: list[float] = []
    rise = 0.0
    for (_, prev), (ts, level) in pairwise(points):
        if level <= prev:
            rise = 0.0
            continue
        already_counted = rise >= JUMP_PERCENT
        rise += level - prev
        if already_counted:
            jumps[-1] = ts  # Same run, move the jump to its end
        elif rise >= JUMP_PERCENT:
            jumps.append(ts)
    return jumps


def estimate_drain(
    daily_means: list[tuple[float, float]],
    now: float,
    last_replaced: float | None = None,
) -> DrainEstimate | None:
    """Fit a least-squares line to (timestamp, mean %) daily points.

    The fit starts at the newest of: the last battery replacement, the last
    level jump, or FIT_DAYS ago, so each estimate only covers the current
    battery and a source that stopped reporting ages out. Returns None with
    fewer than two points.
    """
    points = sorted(p for p in daily_means if math.isfinite(p[1]))
    if len(points) < 2:
        return None

    jumps = _level_jumps(points)

    start = now - FIT_DAYS * SECONDS_PER_DAY
    if jumps:
        start = max(start, jumps[-1])
    if last_replaced is not None:
        start = max(start, last_replaced)

    days = [(ts - start) / SECONDS_PER_DAY for ts, _ in points if ts >= start]
    levels = [level for ts, level in points if ts >= start]
    n = len(days)
    if n < 2:
        return DrainEstimate(rate=0.0, span_days=0, level_jumps=len(jumps))

    mean_day = sum(days) / n
    mean_level = sum(levels) / n
    variance = sum((d - mean_day) ** 2 for d in days)
    slope = (
        sum(
            (d - mean_day) * (v - mean_level) for d, v in zip(days, levels, strict=True)
        )
        / variance
    )

    return DrainEstimate(
        rate=round(-slope, 3) + 0.0,  # + 0.0 drops -0.0
        span_days=round(days[-1] - days[0]),
        level_jumps=len(jumps),
    )

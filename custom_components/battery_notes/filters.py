"""Filters for battery_notes."""

import copy
import logging
import statistics
from collections import Counter, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from numbers import Number
from typing import cast

from .const import WINDOW_SIZE_UNIT_NUMBER_EVENTS, WINDOW_SIZE_UNIT_TIME

_LOGGER = logging.getLogger(__name__)

@dataclass
class _State:
    """Simplified State class.

    The standard State class only accepts string in `state`,
    and we are only interested in two properties.
    """

    last_updated: datetime
    state: str | float | int

class FilterState:
    """State abstraction for filter usage."""

    state: str | float | int

    def __init__(self, state: _State) -> None:
        """Initialize with HA State object."""
        self.timestamp = state.last_updated
        try:
            self.state = float(state.state)
        except ValueError:
            self.state = state.state

    def __str__(self) -> str:
        """Return state as the string representation of FilterState."""
        return str(self.state)

    def __repr__(self) -> str:
        """Return timestamp and state as the representation of FilterState."""
        return f"{self.timestamp} : {self.state}"


class Filter():
    """Base filter class."""

    def __init__(
        self,
        name: str,
        window_size: int | timedelta,
        entity: str,
    ) -> None:
        """Initialize common attributes.

        :param window_size: size of the sliding window that holds previous values
        :param entity: used for debugging only
        """
        if isinstance(window_size, int):
            self.states: deque[FilterState] = deque(maxlen=window_size)
            self.window_unit = WINDOW_SIZE_UNIT_NUMBER_EVENTS
        else:
            self.states = deque(maxlen=0)
            self.window_unit = WINDOW_SIZE_UNIT_TIME
        self.states = deque(maxlen=0)
        self._name = name
        self._entity = entity
        self._skip_processing = False
        self._window_size = window_size
        self._store_raw = False
        self._only_numbers = True

    @property
    def window_size(self) -> int | timedelta:
        """Return window size."""
        return self._window_size

    @property
    def skip_processing(self) -> bool:
        """Return whether the current filter_state should be skipped."""
        return self._skip_processing

    def reset(self) -> None:
        """Reset filter."""
        self.states.clear()

    def _filter_state(self, new_state: FilterState) -> FilterState:
        """Implement filter."""
        raise NotImplementedError

    def filter_state(self, new_state: _State) -> _State:
        """Implement a common interface for filters."""
        fstate = FilterState(new_state)
        if not isinstance(fstate.state, Number):
            raise ValueError(f"State <{fstate.state}> is not a Number")

        filtered = self._filter_state(fstate)

        if self._store_raw:
            self.states.append(copy(FilterState(new_state)))
        else:
            self.states.append(copy(filtered))
        new_state.state = filtered.state
        return new_state

class FilterTimeThrottle(Filter):
    """Time Throttle Filter.

    One sample per time period.
    """

    def __init__(self, *, window_size: timedelta):
        super().__init__(
            window_size,
        )
        self._time_window = window_size
        self._last_emitted_at: datetime | None = None

    def _filter_state(self, new_state: FilterState) -> FilterState:
        """Implement the filter."""
        window_start = new_state.timestamp - self._time_window
        if not self._last_emitted_at or self._last_emitted_at <= window_start:
            self._last_emitted_at = new_state.timestamp
            self._skip_processing = False
        else:
            self._skip_processing = True

        return new_state

class OutlierFilter(Filter):
    """BASIC outlier filter.

    Determines if new state is in a band around the median.
    """

    def __init__(
        self,
        *,
        window_size: int,
        radius: float,
    ) -> None:
        """Initialize Filter.

        :param radius: band radius
        """
        super().__init__(
            window_size
        )
        self._radius = radius
        self._stats_internal: Counter = Counter()
        self._store_raw = True

    def _filter_state(self, new_state: FilterState) -> FilterState:
        """Implement the outlier filter."""

        # We can cast safely here thanks to self._only_numbers = True
        previous_state_values = [cast(float, s.state) for s in self.states]
        new_state_value = cast(float, new_state.state)

        median = statistics.median(previous_state_values) if self.states else 0
        if (
            len(self.states) == self.states.maxlen
            and abs(new_state_value - median) > self._radius
        ):
            self._stats_internal["erasures"] += 1

            _LOGGER.debug(
                "Outlier nr. %s in %s: %s",
                self._stats_internal["erasures"],
                self._entity,
                new_state,
            )
            new_state.state = median
        return new_state

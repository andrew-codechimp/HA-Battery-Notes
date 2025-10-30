"""Filters for battery_notes."""

import logging
import statistics
from typing import cast
from numbers import Number
from datetime import timedelta
from collections import Counter, deque

from .const import WINDOW_SIZE_UNIT_TIME, WINDOW_SIZE_UNIT_NUMBER_EVENTS
from .common import utcnow_no_timezone

_LOGGER = logging.getLogger(__name__)


class FilterState:
    """State abstraction for filter usage."""

    state: str | float | int

    def __init__(self, state: str | float | int) -> None:
        """Initialize with HA State object."""
        self.timestamp = utcnow_no_timezone()
        try:
            self.state = float(state)
        except ValueError:
            self.state = state

    def __str__(self) -> str:
        """Return state as the string representation of FilterState."""
        return str(self.state)

    def __repr__(self) -> str:
        """Return timestamp and state as the representation of FilterState."""
        return f"{self.timestamp} : {self.state}"


class Filter:
    """Base filter class."""

    def __init__(
        self,
        window_size: int | timedelta,
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

    def filter_state(self, new_state: int | float | str) -> int | float | str:
        """Implement a common interface for filters."""
        fstate = FilterState(new_state)
        if not isinstance(fstate.state, Number):
            raise ValueError(f"State <{fstate.state}> is not a Number")

        filtered = self._filter_state(fstate)

        if self._store_raw:
            self.states.append(FilterState(new_state))
        else:
            self.states.append(filtered)
        new_state = filtered.state
        return new_state


class LowOutlierFilter(Filter):
    """Low Outlier filter.

    Determines if new state is in a band around the median, or higher.
    """

    def __init__(
        self,
        window_size: int,
        radius: float,
    ) -> None:
        """Initialize Filter.

        :param radius: band radius
        """
        super().__init__(window_size)
        self._radius = radius
        self._stats_internal: Counter = Counter()
        self._store_raw = True

    def _filter_state(self, new_state: FilterState) -> FilterState:
        """Implement the outlier filter."""

        previous_state_values = [cast(float, s.state) for s in self.states]
        new_state_value = cast(float, new_state.state)
        self._skip_processing = False

        if previous_state_values and new_state_value >= previous_state_values[-1]:
            _LOGGER.debug(
                "New value higher than last previous state, allowing. %s >= %s",
                new_state,
                previous_state_values[-1],
            )
            return new_state

        median = statistics.median(previous_state_values) if self.states else 0

        if (
            len(self.states) == self.states.maxlen
            and abs(new_state_value - median) > self._radius
        ):
            self._skip_processing = True

            if len(self.states) == self.states.maxlen:
                self._stats_internal["erasures"] += 1
                _LOGGER.debug(
                    "Outlier nr. %s: %s",
                    self._stats_internal["erasures"],
                    new_state,
                )

        return new_state

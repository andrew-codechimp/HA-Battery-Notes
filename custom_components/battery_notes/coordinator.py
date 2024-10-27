"""DataUpdateCoordinator for battery notes."""

from __future__ import annotations

import logging
from datetime import datetime

from homeassistant.const import (
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .common import validate_is_float
from .const import (
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_PREVIOUS_BATTERY_LEVEL,
    ATTR_REMOVE,
    ATTR_SOURCE_ENTITY_ID,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_ENABLE_REPLACED,
    CONF_ROUND_BATTERY,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DOMAIN,
    DOMAIN_CONFIG,
    EVENT_BATTERY_INCREASED,
    EVENT_BATTERY_THRESHOLD,
    LAST_REPLACED,
    LAST_REPORTED,
    LAST_REPORTED_LEVEL,
)
from .store import BatteryNotesStorage

_LOGGER = logging.getLogger(__name__)


class BatteryNotesCoordinator(DataUpdateCoordinator):
    """Define an object to hold Battery Notes device."""

    device_id: str = None
    source_entity_id: str = None
    device_name: str
    battery_type: str
    battery_quantity: int
    battery_low_threshold: int
    battery_low_template: str | None
    wrapped_battery: RegistryEntry
    _current_battery_level: str = None
    enable_replaced: bool = True
    _round_battery: bool = False
    _previous_battery_low: bool = None
    _previous_battery_level: str = None
    _battery_low_template_state: bool = False
    _previous_battery_low_template_state: bool = None
    _source_entity_name: str = None

    def __init__(
        self, hass, store: BatteryNotesStorage, wrapped_battery: RegistryEntry
    ):
        """Initialize."""
        self.store = store
        self.wrapped_battery = wrapped_battery

        if DOMAIN_CONFIG in hass.data[DOMAIN]:
            domain_config: dict = hass.data[DOMAIN][DOMAIN_CONFIG]
            self.enable_replaced = domain_config.get(CONF_ENABLE_REPLACED, True)
            self._round_battery = domain_config.get(CONF_ROUND_BATTERY, False)

        super().__init__(hass, _LOGGER, name=DOMAIN)

    @property
    def source_entity_name(self):
        """Get the current name of the source_entity_id."""
        if not self._source_entity_name:
            self._source_entity_name = ""

            if self.source_entity_id:
                entity_registry = er.async_get(self.hass)
                registry_entry = entity_registry.async_get(self.source_entity_id)
                self._source_entity_name = (
                    registry_entry.name or registry_entry.original_name
                )

        return self._source_entity_name

    @property
    def battery_low_template_state(self):
        """Get the current battery low status from a templated device."""
        return self._battery_low_template_state

    @battery_low_template_state.setter
    def battery_low_template_state(self, value):
        """Set the current battery low status from a templated device and fire events if valid."""
        self._battery_low_template_state = value
        if (
            self._previous_battery_low_template_state is not None
            and self.battery_low_template
        ):
            self.hass.bus.async_fire(
                EVENT_BATTERY_THRESHOLD,
                {
                    ATTR_DEVICE_ID: self.device_id or "",
                    ATTR_SOURCE_ENTITY_ID: self.source_entity_id or "",
                    ATTR_DEVICE_NAME: self.device_name,
                    ATTR_BATTERY_LOW: self.battery_low,
                    ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                    ATTR_BATTERY_TYPE: self.battery_type,
                    ATTR_BATTERY_QUANTITY: self.battery_quantity,
                    ATTR_BATTERY_THRESHOLD_REMINDER: False,
                },
            )

            _LOGGER.debug(
                "battery_threshold event fired Low: %s via template", self.battery_low
            )

            if (
                self._previous_battery_low_template_state
                and not self._battery_low_template_state
            ):
                self.hass.bus.async_fire(
                    EVENT_BATTERY_INCREASED,
                    {
                        ATTR_DEVICE_ID: self.device_id or "",
                        ATTR_SOURCE_ENTITY_ID: self.source_entity_id or "",
                        ATTR_DEVICE_NAME: self.device_name,
                        ATTR_BATTERY_LOW: self.battery_low,
                        ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                        ATTR_BATTERY_TYPE: self.battery_type,
                        ATTR_BATTERY_QUANTITY: self.battery_quantity,
                    },
                )

                _LOGGER.debug("battery_increased event fired via template")

        self._previous_battery_low_template_state = value

    @property
    def current_battery_level(self):
        """Get the current battery level."""
        return self._current_battery_level

    @current_battery_level.setter
    def current_battery_level(self, value):
        """Set the current battery level and fire events if valid."""
        self._current_battery_level = value

        if (
            self._previous_battery_level is not None
            and self.battery_low_template is None
        ):
            # Battery low event
            if self.battery_low != self._previous_battery_low:
                self.hass.bus.async_fire(
                    EVENT_BATTERY_THRESHOLD,
                    {
                        ATTR_DEVICE_ID: self.device_id or "",
                        ATTR_SOURCE_ENTITY_ID: self.source_entity_id or "",
                        ATTR_DEVICE_NAME: self.device_name,
                        ATTR_BATTERY_LOW: self.battery_low,
                        ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                        ATTR_BATTERY_TYPE: self.battery_type,
                        ATTR_BATTERY_QUANTITY: self.battery_quantity,
                        ATTR_BATTERY_LEVEL: self.rounded_battery_level,
                        ATTR_PREVIOUS_BATTERY_LEVEL: self.rounded_previous_battery_level,
                        ATTR_BATTERY_THRESHOLD_REMINDER: False,
                    },
                )

                _LOGGER.debug("battery_threshold event fired Low: %s", self.battery_low)

            # Battery increased event
            increase_threshold = DEFAULT_BATTERY_INCREASE_THRESHOLD
            if DOMAIN_CONFIG in self.hass.data[DOMAIN]:
                domain_config: dict = self.hass.data[DOMAIN][DOMAIN_CONFIG]
                increase_threshold = domain_config.get(
                    CONF_BATTERY_INCREASE_THRESHOLD, DEFAULT_BATTERY_INCREASE_THRESHOLD
                )

            if self._current_battery_level not in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
                if (
                    self._current_battery_level
                    and self._previous_battery_level
                    and float(self._current_battery_level)
                    >= (float(self._previous_battery_level) + increase_threshold)
                ):
                    self.hass.bus.async_fire(
                        EVENT_BATTERY_INCREASED,
                        {
                            ATTR_DEVICE_ID: self.device_id or "",
                            ATTR_SOURCE_ENTITY_ID: self.source_entity_id or "",
                            ATTR_DEVICE_NAME: self.device_name,
                            ATTR_BATTERY_LOW: self.battery_low,
                            ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                            ATTR_BATTERY_TYPE: self.battery_type,
                            ATTR_BATTERY_QUANTITY: self.battery_quantity,
                            ATTR_BATTERY_LEVEL: self.rounded_battery_level,
                            ATTR_PREVIOUS_BATTERY_LEVEL: self.rounded_previous_battery_level,
                        },
                    )

                    _LOGGER.debug("battery_increased event fired")

        if self._current_battery_level not in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
            self.last_reported = datetime.utcnow()
            self.last_reported_level = self._current_battery_level
            self._previous_battery_low = self.battery_low
            self._previous_battery_level = self._current_battery_level

    @property
    def battery_type_and_quantity(self) -> str:
        """Merge battery type & quantity."""
        if self.battery_quantity and int(self.battery_quantity) > 1:
            return str(self.battery_quantity) + "× " + self.battery_type
        return self.battery_type

    @property
    def last_replaced(self) -> datetime | None:
        """Get the last replaced datetime."""
        if self.source_entity_id:
            entry = self.store.async_get_entity(self.source_entity_id)
        else:
            entry = self.store.async_get_device(self.device_id)

        if entry:
            if LAST_REPLACED in entry and entry[LAST_REPLACED] is not None:
                last_replaced_date = datetime.fromisoformat(
                    str(entry[LAST_REPLACED]) + "+00:00"
                )
                return last_replaced_date
        return None

    @last_replaced.setter
    def last_replaced(self, value):
        """Set the last replaced datetime and store it."""
        entry = {LAST_REPLACED: value}

        if self.source_entity_id:
            self.async_update_entity_config(entity_id=self.source_entity_id, data=entry)
        else:
            self.async_update_device_config(device_id=self.device_id, data=entry)

    @property
    def last_reported(self) -> datetime | None:
        """Get the last reported datetime."""

        if self.source_entity_id:
            entry = self.store.async_get_entity(self.source_entity_id)
        else:
            entry = self.store.async_get_device(self.device_id)

        if entry:
            if LAST_REPORTED in entry:
                if entry[LAST_REPORTED]:
                    last_reported_date = datetime.fromisoformat(
                        str(entry[LAST_REPORTED]) + "+00:00"
                    )
                    return last_reported_date

        return None

    @last_reported.setter
    def last_reported(self, value):
        """Set the last reported datetime and store it."""
        entry = {LAST_REPORTED: value}

        if self.source_entity_id:
            self.async_update_entity_config(entity_id=self.source_entity_id, data=entry)
        else:
            self.async_update_device_config(device_id=self.device_id, data=entry)

    @property
    def last_reported_level(self) -> float | None:
        """Get the last reported level."""

        if self.source_entity_id:
            entry = self.store.async_get_entity(self.source_entity_id)
        else:
            entry = self.store.async_get_device(self.device_id)

        if entry:
            if LAST_REPORTED_LEVEL in entry:
                if entry[LAST_REPORTED_LEVEL]:
                    last_reported_level = float(entry[LAST_REPORTED_LEVEL])
                    return self._rounded_level(last_reported_level)
        return None

    @last_reported_level.setter
    def last_reported_level(self, value):
        """Set the last reported level and store it."""
        entry = {"battery_last_reported_level": value}

        if self.source_entity_id:
            self.async_update_entity_config(entity_id=self.source_entity_id, data=entry)
        else:
            self.async_update_device_config(device_id=self.device_id, data=entry)

    @property
    def battery_low(self) -> bool:
        """Check if battery low against threshold."""
        if self.battery_low_template:
            return self.battery_low_template_state
        else:
            if validate_is_float(self.current_battery_level):
                return bool(
                    float(self.current_battery_level) < self.battery_low_threshold
                )

        return False

    @property
    def rounded_battery_level(self) -> float:
        """Return the battery level, rounded if preferred."""
        return self._rounded_level(self.current_battery_level)

    @property
    def rounded_previous_battery_level(self) -> float:
        """Return the previous battery level, rounded if preferred."""
        return self._rounded_level(self._previous_battery_level)

    def _rounded_level(self, value) -> float:
        """Round the level, if preferred."""
        if validate_is_float(value):
            return round(float(value), None if self._round_battery else 1)
        else:
            return value

    async def _async_update_data(self):
        """Update data."""
        self.async_set_updated_data(None)

        _LOGGER.debug("Update coordinator")

    def async_update_device_config(self, device_id: str, data: dict):
        """Conditional create, update or remove device from store."""

        if ATTR_REMOVE in data:
            self.store.async_delete_device(device_id)
        elif self.store.async_get_device(device_id):
            self.store.async_update_device(device_id, data)
        else:
            self.store.async_create_device(device_id, data)

    def async_update_entity_config(self, entity_id: str, data: dict):
        """Conditional create, update or remove entity from store."""

        if ATTR_REMOVE in data:
            self.store.async_delete_entity(entity_id)
        elif self.store.async_get_entity(entity_id):
            self.store.async_update_entity(entity_id, data)
        else:
            self.store.async_create_entity(entity_id, data)

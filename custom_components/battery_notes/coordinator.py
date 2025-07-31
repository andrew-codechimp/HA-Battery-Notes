"""DataUpdateCoordinator for battery notes."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.hass_dict import HassKey

from .common import utcnow_no_timezone, validate_is_float
from .const import (
    ATTR_BATTERY_LAST_REPLACED,
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_LOW_THRESHOLD,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_PREVIOUS_BATTERY_LEVEL,
    ATTR_REMOVE,
    ATTR_SOURCE_ENTITY_ID,
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_FILTER_OUTLIERS,
    CONF_SOURCE_ENTITY_ID,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DEFAULT_LIBRARY_URL,
    DEFAULT_SCHEMA_URL,
    DOMAIN,
    EVENT_BATTERY_INCREASED,
    EVENT_BATTERY_THRESHOLD,
    LAST_REPLACED,
    LAST_REPORTED,
    LAST_REPORTED_LEVEL,
)
from .filters import LowOutlierFilter
from .store import BatteryNotesStorage

_LOGGER = logging.getLogger(__name__)

@dataclass
class BatteryNotesDomainConfig:
    """Class for sharing config data within the BatteryNotes integration."""
    enable_autodiscovery: bool = True
    show_all_devices: bool = False
    enable_replaced: bool = True
    hide_battery: bool = False
    round_battery: bool = False
    default_battery_low_threshold: int = DEFAULT_BATTERY_LOW_THRESHOLD
    battery_increased_threshod: int = DEFAULT_BATTERY_INCREASE_THRESHOLD
    library_url: str = DEFAULT_LIBRARY_URL
    schema_url: str = DEFAULT_SCHEMA_URL
    library_last_update: datetime | None = None
    user_library: str = ""
    store: BatteryNotesStorage | None = None

MY_KEY: HassKey[BatteryNotesDomainConfig] = HassKey(DOMAIN)

type BatteryNotesConfigEntry = ConfigEntry[BatteryNotesData]

@dataclass
class BatteryNotesData:
    """Class for sharing data within the BatteryNotes integration."""

    domain_config: BatteryNotesDomainConfig
    store: BatteryNotesStorage
    coordinator: BatteryNotesCoordinator | None = None


class BatteryNotesCoordinator(DataUpdateCoordinator[None]):
    """Define an object to hold Battery Notes device."""

    config_entry: BatteryNotesConfigEntry
    device_id: str | None = None
    source_entity_id: str | None = None
    device_name: str
    battery_type: str
    battery_quantity: int
    battery_low_threshold: int
    battery_low_template: str | None
    wrapped_battery: RegistryEntry | None = None
    wrapped_battery_low: RegistryEntry | None = None
    _current_battery_level: str | None = None
    _previous_battery_low: bool | None = None
    _previous_battery_level: str | None = None
    _battery_low_template_state: bool = False
    _previous_battery_low_template_state: bool | None = None
    _battery_low_binary_state: bool = False
    _previous_battery_low_binary_state: bool | None = None
    _source_entity_name: str | None = None
    _outlier_filter: LowOutlierFilter | None = None

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: BatteryNotesConfigEntry,
    ):
        """Initialize."""
        super().__init__(hass, _LOGGER, config_entry=config_entry, name=DOMAIN)

        self.reset_jobs: list[CALLBACK_TYPE] = []

        self.config_entry = config_entry

        self.device_id = config_entry.data.get(CONF_DEVICE_ID, None)
        self.source_entity_id = config_entry.data.get(CONF_SOURCE_ENTITY_ID, None)

        self._link_device()

        assert(self.device_name)

        self.battery_type = cast(str, self.config_entry.data.get(CONF_BATTERY_TYPE))
        try:
            self.battery_quantity = cast(
                int, self.config_entry.data.get(CONF_BATTERY_QUANTITY)
            )
        except ValueError:
            self.battery_quantity = 1

        self.battery_low_threshold = int(
            self.config_entry.data.get(CONF_BATTERY_LOW_THRESHOLD, 0)
        )

        if hasattr(self.config_entry, "runtime_data"):
            if self.battery_low_threshold == 0:
                self.battery_low_threshold = self.config_entry.runtime_data.domain_config.default_battery_low_threshold

        self.battery_low_template = self.config_entry.data.get(
            CONF_BATTERY_LOW_TEMPLATE
        )

        if config_entry.data.get(CONF_FILTER_OUTLIERS, False):
            self._outlier_filter = LowOutlierFilter(window_size=3, radius=80)
            _LOGGER.debug("Outlier filter enabled")

        if self.wrapped_battery:
            _LOGGER.debug(
                "%s low threshold set at %d",
                self.wrapped_battery.entity_id,
                self.battery_low_threshold,
            )

        # If there is not a last replaced, set to device created date if not epoch
        device_registry = dr.async_get(self.hass)
        entity_registry = er.async_get(self.hass)
        if not self.last_replaced:
            last_replaced = None
            if self.device_id:
                device_entry = device_registry.async_get(self.device_id)

                if device_entry and device_entry.created_at.year > 1970:
                    last_replaced = device_entry.created_at.strftime(
                        "%Y-%m-%dT%H:%M:%S:%f"
                    )
            elif self.source_entity_id:
                entity = entity_registry.async_get(self.source_entity_id)
                if entity and entity.created_at.year > 1970:
                    last_replaced = entity.created_at.strftime("%Y-%m-%dT%H:%M:%S:%f")

            _LOGGER.debug(
                "Defaulting %s battery last replaced to %s",
                self.source_entity_id or self.device_id,
                last_replaced,
            )

            if last_replaced:
                self.last_replaced = datetime.fromisoformat(last_replaced)

        # If there is not a last_reported set to now
        if not self.last_reported:
            last_reported = utcnow_no_timezone()
            _LOGGER.debug(
                "Defaulting %s battery last reported to %s",
                self.source_entity_id or self.device_id,
                last_reported,
            )
            self.last_reported = last_reported

    def _link_device(self) -> bool:
        """Get the device name."""
        device_registry = dr.async_get(self.hass)
        entity_registry = er.async_get(self.hass)

        if self.source_entity_id:
            entity = entity_registry.async_get(self.source_entity_id)

            if not entity:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"missing_device_{self.config_entry.entry_id}",
                    data={
                        "entry_id": self.config_entry.entry_id,
                        "device_id": self.device_id,
                        "source_entity_id": self.source_entity_id,
                    },
                    is_fixable=True,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="missing_device",
                    translation_placeholders={
                        "name": self.config_entry.title,
                    },
                )

                _LOGGER.warning(
                    "%s is orphaned, unable to find entity %s",
                    self.config_entry.entry_id,
                    self.source_entity_id,
                )
                return False

            device_class = entity.device_class or entity.original_device_class
            if (
                device_class == SensorDeviceClass.BATTERY
                and entity.unit_of_measurement == PERCENTAGE
            ):
                self.wrapped_battery = entity
            else:
                _LOGGER.debug(
                    "%s is not a battery entity device_class: %s unit_of_measurement: %s",
                    self.source_entity_id,
                    device_class,
                    entity.unit_of_measurement,
                )

            if entity.device_id:
                device_entry = device_registry.async_get(entity.device_id)
                if device_entry:
                    self.device_name = (
                        device_entry.name_by_user
                        or device_entry.name
                        or self.config_entry.title
                    )
                else:
                    self.device_name = self.config_entry.title
            else:
                self.device_name = self.config_entry.title
        else:
            for entity in entity_registry.entities.values():

                if not entity.device_id or entity.device_id != self.device_id:
                    continue
                if (
                    not entity.domain
                    or entity.domain not in [SENSOR_DOMAIN, BINARY_SENSOR_DOMAIN]
                ):
                    continue
                if not entity.platform or entity.platform == DOMAIN:
                    continue

                if entity.disabled:
                    continue

                device_class = entity.device_class or entity.original_device_class

                if entity.domain == SENSOR_DOMAIN:
                    if device_class != SensorDeviceClass.BATTERY:
                        continue
                    if entity.unit_of_measurement != PERCENTAGE:
                        continue
                    self.wrapped_battery = entity_registry.async_get(entity.entity_id)
                    break

                if entity.domain == BINARY_SENSOR_DOMAIN:
                    if device_class != BinarySensorDeviceClass.BATTERY:
                        continue
                    self.wrapped_battery_low = entity_registry.async_get(
                        entity.entity_id
                    )
                    if self.wrapped_battery:
                        break

            device_entry = None
            if self.device_id:
                device_entry = device_registry.async_get(self.device_id)
            if device_entry:
                self.device_name = (
                    device_entry.name_by_user or device_entry.name or self.config_entry.title
                )
            else:
                self.device_name = self.config_entry.title

                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    f"missing_device_{self.config_entry.entry_id}",
                    data={
                        "entry_id": self.config_entry.entry_id,
                        "device_id": self.device_id,
                        "source_entity_id": self.source_entity_id,
                    },
                    is_fixable=True,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key="missing_device",
                    translation_placeholders={
                        "name": self.config_entry.title,
                    },
                )

                _LOGGER.warning(
                    "%s is orphaned, unable to find device %s",
                    self.config_entry.entry_id,
                    self.device_id,
                )
                return False

        return True

    @property
    def fake_device(self) -> bool:
        """Return if an actual device registry entry."""
        if self.config_entry.data.get(CONF_SOURCE_ENTITY_ID, None):
            if self.config_entry.data.get(CONF_DEVICE_ID, None) is None:
                return True
        return False

    @property
    def source_entity_name(self):
        """Get the current name of the source_entity_id."""
        if not self._source_entity_name:
            self._source_entity_name = ""

            if self.source_entity_id:
                entity_registry = er.async_get(self.hass)
                device_registry = dr.async_get(self.hass)
                registry_entry = entity_registry.async_get(self.source_entity_id)
                device_entry = device_registry.async_get(self.device_id) if self.device_id else None
                assert(registry_entry)

                if registry_entry.name is None and registry_entry.has_entity_name and device_entry:
                    self._source_entity_name = (
                        registry_entry.name or registry_entry.original_name or device_entry.name_by_user or device_entry.name or self.source_entity_id
                    )
                else:
                    self._source_entity_name = (
                        registry_entry.name or registry_entry.original_name or self.source_entity_id
                    )

            assert(self._source_entity_name)

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
            and value not in [
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ]
        ):
            self.hass.bus.async_fire(
                EVENT_BATTERY_THRESHOLD,
                {
                    ATTR_DEVICE_ID: self.device_id or "",
                    ATTR_SOURCE_ENTITY_ID: self.source_entity_id or "",
                    ATTR_DEVICE_NAME: self.device_name,
                    ATTR_BATTERY_LOW: self.battery_low,
                    ATTR_BATTERY_LOW_THRESHOLD: self.battery_low_threshold,
                    ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                    ATTR_BATTERY_TYPE: self.battery_type,
                    ATTR_BATTERY_QUANTITY: self.battery_quantity,
                    ATTR_BATTERY_LEVEL: 0,
                    ATTR_PREVIOUS_BATTERY_LEVEL: 100,
                    ATTR_BATTERY_LAST_REPLACED: self.last_replaced,
                    ATTR_BATTERY_THRESHOLD_REMINDER: False,
                },
            )

            _LOGGER.debug(
                "battery_threshold event fired Low: %s via template", self.battery_low
            )

            if (
                self._previous_battery_low_template_state
                and not self._battery_low_template_state
                and value not in [
                    STATE_UNAVAILABLE,
                    STATE_UNKNOWN,
                ]
            ):
                self.hass.bus.async_fire(
                    EVENT_BATTERY_INCREASED,
                    {
                        ATTR_DEVICE_ID: self.device_id or "",
                        ATTR_SOURCE_ENTITY_ID: self.source_entity_id or "",
                        ATTR_DEVICE_NAME: self.device_name,
                        ATTR_BATTERY_LOW: self.battery_low,
                        ATTR_BATTERY_LOW_THRESHOLD: self.battery_low_threshold,
                        ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                        ATTR_BATTERY_TYPE: self.battery_type,
                        ATTR_BATTERY_QUANTITY: self.battery_quantity,
                        ATTR_BATTERY_LEVEL: 100,
                        ATTR_PREVIOUS_BATTERY_LEVEL: 0,
                        ATTR_BATTERY_LAST_REPLACED: self.last_replaced,
                    },
                )

                _LOGGER.debug("battery_increased event fired via template")


        self._previous_battery_low_template_state = value

    @property
    def battery_low_binary_state(self):
        """Get the current battery low status from a binary sensor."""
        return self._battery_low_binary_state

    @battery_low_binary_state.setter
    def battery_low_binary_state(self, value):
        """Set the current battery low status from a binary sensor and fire events if valid."""
        self._battery_low_binary_state = value
        if (self._previous_battery_low_binary_state is not None
            and value not in [
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ]):
            self.hass.bus.async_fire(
                EVENT_BATTERY_THRESHOLD,
                {
                    ATTR_DEVICE_ID: self.device_id or "",
                    ATTR_SOURCE_ENTITY_ID: self.source_entity_id or "",
                    ATTR_DEVICE_NAME: self.device_name,
                    ATTR_BATTERY_LOW: self.battery_low,
                    ATTR_BATTERY_LOW_THRESHOLD: self.battery_low_threshold,
                    ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                    ATTR_BATTERY_TYPE: self.battery_type,
                    ATTR_BATTERY_QUANTITY: self.battery_quantity,
                    ATTR_BATTERY_LEVEL: 0,
                    ATTR_PREVIOUS_BATTERY_LEVEL: 100,
                    ATTR_BATTERY_LAST_REPLACED: self.last_replaced,
                    ATTR_BATTERY_THRESHOLD_REMINDER: False,
                },
            )

            _LOGGER.debug(
                "battery_threshold event fired Low: %s via binary sensor",
                self.battery_low,
            )

            if (
                self._previous_battery_low_binary_state
                and not self._battery_low_binary_state
                and value not in [
                    STATE_UNAVAILABLE,
                    STATE_UNKNOWN,
                ]
            ):
                self.hass.bus.async_fire(
                    EVENT_BATTERY_INCREASED,
                    {
                        ATTR_DEVICE_ID: self.device_id or "",
                        ATTR_SOURCE_ENTITY_ID: self.source_entity_id or "",
                        ATTR_DEVICE_NAME: self.device_name,
                        ATTR_BATTERY_LOW: self.battery_low,
                        ATTR_BATTERY_LOW_THRESHOLD: self.battery_low_threshold,
                        ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                        ATTR_BATTERY_TYPE: self.battery_type,
                        ATTR_BATTERY_QUANTITY: self.battery_quantity,
                        ATTR_BATTERY_LEVEL: 100,
                        ATTR_PREVIOUS_BATTERY_LEVEL: 0,
                        ATTR_BATTERY_LAST_REPLACED: self.last_replaced,
                    },
                )

                _LOGGER.debug("battery_increased event fired via binary sensor")

        self._previous_battery_low_binary_state = value

    @property
    def current_battery_level(self):
        """Get the current battery level."""
        return self._current_battery_level

    @current_battery_level.setter
    def current_battery_level(self, value):
        """Set the current battery level and fire events if valid."""

        if self._outlier_filter:
            if value not in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
                self._outlier_filter.filter_state(float(value))

                _LOGGER.debug(
                    "Checking outlier (%s=%s) -> %s",
                    self.device_id or self.source_entity_id or "",
                    value,
                    "skip" if self._outlier_filter.skip_processing else self._outlier_filter.filter_state(value),
                )
                if self._outlier_filter.skip_processing:
                    return

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
                        ATTR_BATTERY_LOW_THRESHOLD: self.battery_low_threshold,
                        ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                        ATTR_BATTERY_TYPE: self.battery_type,
                        ATTR_BATTERY_QUANTITY: self.battery_quantity,
                        ATTR_BATTERY_LEVEL: self.rounded_battery_level,
                        ATTR_PREVIOUS_BATTERY_LEVEL: self.rounded_previous_battery_level,
                        ATTR_BATTERY_LAST_REPLACED: self.last_replaced,
                        ATTR_BATTERY_THRESHOLD_REMINDER: False,
                    },
                )

                _LOGGER.debug("battery_threshold event fired Low: %s", self.battery_low)

            # Battery increased event
            increase_threshold = self.config_entry.runtime_data.domain_config.battery_increased_threshod

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
                            ATTR_BATTERY_LOW_THRESHOLD: self.battery_low_threshold,
                            ATTR_BATTERY_TYPE_AND_QUANTITY: self.battery_type_and_quantity,
                            ATTR_BATTERY_TYPE: self.battery_type,
                            ATTR_BATTERY_QUANTITY: self.battery_quantity,
                            ATTR_BATTERY_LEVEL: self.rounded_battery_level,
                            ATTR_PREVIOUS_BATTERY_LEVEL: self.rounded_previous_battery_level,
                            ATTR_BATTERY_LAST_REPLACED: self.last_replaced,
                        },
                    )

                    _LOGGER.debug("battery_increased event fired")

        if self._current_battery_level not in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
            self.last_reported = utcnow_no_timezone()
            self.last_reported_level = cast(float, self._current_battery_level)
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
        if not hasattr(self.config_entry, "runtime_data"):
            return None

        if self.source_entity_id:
            entry = self.config_entry.runtime_data.store.async_get_entity(self.source_entity_id)
        else:
            entry = self.config_entry.runtime_data.store.async_get_device(self.device_id)

        if entry:
            if LAST_REPLACED in entry and entry[LAST_REPLACED] is not None:
                last_replaced_date = datetime.fromisoformat(
                    str(entry[LAST_REPLACED]) + "+00:00"
                )
                return last_replaced_date
        return None

    @last_replaced.setter
    def last_replaced(self, value: datetime):
        """Set the last replaced datetime and store it."""
        if not hasattr(self.config_entry, "runtime_data"):
            return

        entry = {LAST_REPLACED: value}

        if self.source_entity_id:
            self.async_update_entity_config(entity_id=self.source_entity_id, data=entry)
        elif self.device_id:
            self.async_update_device_config(device_id=self.device_id, data=entry)

    @property
    def last_reported(self) -> datetime | None:
        """Get the last reported datetime."""

        if not hasattr(self.config_entry, "runtime_data"):
            return None

        if self.source_entity_id:
            entry = self.config_entry.runtime_data.store.async_get_entity(self.source_entity_id)
        else:
            entry = self.config_entry.runtime_data.store.async_get_device(self.device_id)

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

        if not hasattr(self.config_entry, "runtime_data"):
            return

        entry = {LAST_REPORTED: value}

        if self.source_entity_id:
            self.async_update_entity_config(entity_id=self.source_entity_id, data=entry)
        else:
            assert(self.device_id)
            self.async_update_device_config(device_id=self.device_id, data=entry)

    @property
    def last_reported_level(self) -> float | None:
        """Get the last reported level."""
        if not hasattr(self.config_entry, "runtime_data"):
            return None

        if self.source_entity_id:
            entry = self.config_entry.runtime_data.store.async_get_entity(self.source_entity_id)
        else:
            entry = self.config_entry.runtime_data.store.async_get_device(self.device_id)

        if entry:
            if LAST_REPORTED_LEVEL in entry:
                if entry[LAST_REPORTED_LEVEL]:
                    last_reported_level = float(entry[LAST_REPORTED_LEVEL])
                    return self._rounded_level(last_reported_level)
        return None

    @last_reported_level.setter
    def last_reported_level(self, value: float):
        """Set the last reported level and store it."""
        entry = {"battery_last_reported_level": value}

        if self.source_entity_id:
            self.async_update_entity_config(entity_id=self.source_entity_id, data=entry)
        else:
            assert(self.device_id)
            self.async_update_device_config(device_id=self.device_id, data=entry)

    @property
    def battery_low(self) -> bool:
        """Check if battery low against threshold."""
        if self.battery_low_template:
            return self.battery_low_template_state
        elif self.wrapped_battery:
            if validate_is_float(self.current_battery_level):
                return bool(
                    float(self.current_battery_level) < self.battery_low_threshold
                )
        elif self.wrapped_battery_low:
            return self.battery_low_binary_state

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
            return round(float(value), None if self.config_entry.runtime_data.domain_config.round_battery else 1)
        else:
            return value

    async def _async_update_data(self):
        """Update data."""
        self.async_set_updated_data(None)

        _LOGGER.debug("Update coordinator")

    def async_update_device_config(self, device_id: str, data: dict):
        """Conditional create, update or remove device from store."""

        if not hasattr(self.config_entry, "runtime_data"):
            return

        if ATTR_REMOVE in data:
            self.config_entry.runtime_data.store.async_delete_device(device_id)
        elif self.config_entry.runtime_data.store.async_get_device(device_id):
            self.config_entry.runtime_data.store.async_update_device(device_id, data)
        else:
            self.config_entry.runtime_data.store.async_create_device(device_id, data)

    def async_update_entity_config(self, entity_id: str, data: dict):
        """Conditional create, update or remove entity from store."""

        if not hasattr(self.config_entry, "runtime_data"):
            return

        if ATTR_REMOVE in data:
            self.config_entry.runtime_data.store.async_delete_entity(entity_id)
        elif self.config_entry.runtime_data.store.async_get_entity(entity_id):
            self.config_entry.runtime_data.store.async_update_entity(entity_id, data)
        else:
            self.config_entry.runtime_data.store.async_create_entity(entity_id, data)

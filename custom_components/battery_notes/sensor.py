"""Sensor platform for battery_notes."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import (
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
)
from homeassistant.helpers.event import (
    EventStateChangedData,
    EventStateReportedData,
    async_track_state_change_event,
    async_track_state_report_event,
)
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .common import validate_is_float
from .const import (
    ATTR_BATTERY_INCREASE_THRESHOLD,
    ATTR_BATTERY_LAST_REPLACED,
    ATTR_BATTERY_LAST_REPORTED,
    ATTR_BATTERY_LAST_REPORTED_LEVEL,
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_LOW_THRESHOLD,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_NOTE,
    ATTR_SOURCE_ENTITY_ID,
    DOMAIN,
    STATE_WRITE_INTERVAL_SECONDS,
    SUBENTRY_BATTERY_NOTE,
)
from .coordinator import (
    BatteryNotesConfigEntry,
    BatteryNotesSubentryCoordinator,
)
from .entity import BatteryNotesEntity, BatteryNotesEntityDescription
from .template_helpers import TemplateTrackingMixin


@dataclass(frozen=True, kw_only=True)
class BatteryNotesSensorEntityDescription(
    BatteryNotesEntityDescription,
    SensorEntityDescription,
):
    """Describes Battery Notes sensor entity."""

    unique_id_suffix: str


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BatteryNotesConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""

    domain_config = config_entry.runtime_data.domain_config

    for subentry in config_entry.get_subentries_of_type(SUBENTRY_BATTERY_NOTE):
        assert config_entry.runtime_data.subentry_coordinators
        coordinator = config_entry.runtime_data.subentry_coordinators.get(
            subentry.subentry_id
        )
        assert coordinator

        if coordinator.is_orphaned:
            _LOGGER.debug(
                "Skipping sensor creation for orphaned subentry: %s",
                subentry.title,
            )
            continue

        type_sensor_entity_description = BatteryNotesSensorEntityDescription(
            unique_id_suffix="_battery_type",
            key="battery_type",
            translation_key="battery_type",
            entity_category=EntityCategory.DIAGNOSTIC,
            entity_type="sensor",
        )

        last_replaced_sensor_entity_description = BatteryNotesSensorEntityDescription(
            unique_id_suffix="_battery_last_replaced",
            key="battery_last_replaced",
            translation_key="battery_last_replaced",
            entity_category=EntityCategory.DIAGNOSTIC,
            device_class=SensorDeviceClass.TIMESTAMP,
            entity_registry_enabled_default=domain_config.enable_replaced,
            entity_type="sensor",
        )

        battery_plus_sensor_entity_description = BatteryNotesSensorEntityDescription(
            unique_id_suffix="_battery_plus",
            key="battery_plus",
            translation_key="battery_plus",
            device_class=SensorDeviceClass.BATTERY,
            suggested_display_precision=0 if domain_config.round_battery else 1,
            entity_type="sensor",
            require_device=True,
        )

        entities = [
            BatteryNotesTypeSensor(
                hass,
                config_entry,
                subentry,
                type_sensor_entity_description,
                coordinator,
                f"{subentry.unique_id}{type_sensor_entity_description.unique_id_suffix}",
            ),
            BatteryNotesLastReplacedSensor(
                hass,
                config_entry,
                subentry,
                last_replaced_sensor_entity_description,
                coordinator,
                last_replaced_sensor_entity_description,
                f"{subentry.unique_id}{last_replaced_sensor_entity_description.unique_id_suffix}",
            ),
        ]

        if coordinator.battery_percentage_template is not None:
            entities.append(
                BatteryNotesBatteryPlusTemplateSensor(
                    hass,
                    config_entry,
                    subentry,
                    battery_plus_sensor_entity_description,
                    coordinator,
                    f"{subentry.unique_id}{battery_plus_sensor_entity_description.unique_id_suffix}",
                    domain_config.enable_replaced,
                    domain_config.round_battery,
                    coordinator.battery_percentage_template,
                )
            )
        elif coordinator.wrapped_battery is not None:
            entities.append(
                BatteryNotesBatteryPlusSensor(
                    hass,
                    config_entry,
                    subentry,
                    battery_plus_sensor_entity_description,
                    coordinator,
                    f"{subentry.unique_id}{battery_plus_sensor_entity_description.unique_id_suffix}",
                    domain_config.enable_replaced,
                    domain_config.round_battery,
                )
            )

        async_add_entities(
            entities,
            config_subentry_id=subentry.subentry_id,
        )


class BatteryNotesTypeSensor(BatteryNotesEntity, RestoreSensor):
    """Represents a battery note type sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription
    _unrecorded_attributes = frozenset(
        {
            ATTR_BATTERY_QUANTITY,
            ATTR_BATTERY_TYPE,
            ATTR_NOTE,
        }
    )

    def __init__(  # noqa: PLR0913
        self,
        hass,
        config_entry: BatteryNotesConfigEntry,  # noqa: ARG002
        subentry: ConfigSubentry,  # noqa: ARG002
        entity_description: BatteryNotesEntityDescription,
        coordinator: BatteryNotesSubentryCoordinator,
        unique_id: str,
    ) -> None:
        # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__(
            hass=hass, entity_description=entity_description, coordinator=coordinator
        )

        self._attr_unique_id = unique_id

        self._battery_type = coordinator.battery_type
        self._battery_quantity = coordinator.battery_quantity

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_sensor_data()
        if state:
            self._attr_native_value = state.native_value

        # Update entity options, this is needed for legacy v1 support
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {
                    "entity_id": self._attr_unique_id,
                },
            )

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""
        return self.coordinator.battery_type_and_quantity

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes of the battery type."""

        attrs = {
            ATTR_BATTERY_QUANTITY: self.coordinator.battery_quantity,
            ATTR_BATTERY_TYPE: self.coordinator.battery_type,
            ATTR_NOTE: self.coordinator.battery_note,
        }

        super_attrs = super().extra_state_attributes
        if super_attrs:
            attrs.update(super_attrs)
        return attrs


class BatteryNotesLastReplacedSensor(BatteryNotesEntity, SensorEntity):
    """Represents a battery note sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription

    def __init__(  # noqa: PLR0913
        self,
        hass,
        config_entry: BatteryNotesConfigEntry,  # noqa: ARG002
        subentry: ConfigSubentry,  # noqa: ARG002
        entity_description: BatteryNotesEntityDescription,
        coordinator: BatteryNotesSubentryCoordinator,
        description: BatteryNotesSensorEntityDescription,
        unique_id: str,
    ) -> None:
        # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__(
            hass=hass, entity_description=entity_description, coordinator=coordinator
        )

        self._attr_device_class = description.device_class
        self._attr_unique_id = unique_id
        self._device_id = coordinator.device_id
        self._source_entity_id = coordinator.source_entity_id
        self._native_value: datetime | None = None

        self._set_native_value(log_on_error=False)

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()

    def _set_native_value(self, log_on_error=True):  # noqa: ARG002
        if last_replaced := self.coordinator.last_replaced:
            self._native_value = last_replaced

            return True
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if last_replaced := self.coordinator.last_replaced:
            self._native_value = last_replaced

            self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | None:
        """Return the native value of the sensor."""
        return self._native_value


class BatteryNotesBatteryPlusBaseSensor(BatteryNotesEntity, RestoreSensor):
    """Base class for Battery Plus sensors."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription
    _unrecorded_attributes = frozenset(
        {
            ATTR_BATTERY_QUANTITY,
            ATTR_BATTERY_TYPE,
            ATTR_BATTERY_TYPE_AND_QUANTITY,
            ATTR_NOTE,
            ATTR_BATTERY_INCREASE_THRESHOLD,
            ATTR_BATTERY_LOW,
            ATTR_BATTERY_LOW_THRESHOLD,
            ATTR_BATTERY_LAST_REPORTED,
            ATTR_BATTERY_LAST_REPORTED_LEVEL,
            ATTR_BATTERY_LAST_REPLACED,
            ATTR_DEVICE_ID,
            ATTR_SOURCE_ENTITY_ID,
            ATTR_DEVICE_NAME,
        }
    )

    def __init__(  # noqa: PLR0913
        self,
        hass: HomeAssistant,
        config_entry: BatteryNotesConfigEntry,
        subentry: ConfigSubentry,  # noqa: ARG002
        entity_description: BatteryNotesEntityDescription,
        coordinator: BatteryNotesSubentryCoordinator,
        unique_id: str,
        enable_replaced: bool,
        round_battery: bool,
    ) -> None:
        # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__(
            hass=hass, entity_description=entity_description, coordinator=coordinator
        )

        self.config_entry = config_entry

        self._attr_unique_id = unique_id
        self.enable_replaced = enable_replaced
        self.round_battery = round_battery

        self._device_id = coordinator.device_id
        self._source_entity_id = coordinator.source_entity_id

        entity_category = (
            coordinator.wrapped_battery.entity_category
            if coordinator.wrapped_battery
            else None
        )

        self._attr_entity_category = entity_category
        self._attr_unique_id = unique_id

        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE

        self._last_ha_state_write: datetime | None = None
        self._last_written_battery_level: float | None = None
        self._last_written_last_replaced: datetime | None = None
        self._last_written_available: bool | None = None

    @callback
    def _write_tracked_ha_state(self) -> None:
        """Write state at startup, on value changes, on important attributes or when interval elapsed."""
        native_value = self._attr_native_value
        if isinstance(native_value, int | float | str):
            try:
                current_battery_level = float(native_value)
            except ValueError:
                current_battery_level = None
        else:
            current_battery_level = None

        current_last_replaced = (
            self.coordinator.last_replaced if self.enable_replaced else None
        )

        if self._last_ha_state_write is not None:
            if (
                current_battery_level == self._last_written_battery_level
                and current_last_replaced == self._last_written_last_replaced
                and self.available == self._last_written_available
                and (dt_util.utcnow() - self._last_ha_state_write).total_seconds()
                < STATE_WRITE_INTERVAL_SECONDS
            ):
                return

        self._last_ha_state_write = dt_util.utcnow()
        self._last_written_battery_level = current_battery_level
        self._last_written_last_replaced = current_last_replaced
        self._last_written_available = self.available
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes of the battery type."""

        # Battery related attributes
        attrs = {
            ATTR_BATTERY_QUANTITY: self.coordinator.battery_quantity,
            ATTR_BATTERY_TYPE: self.coordinator.battery_type,
            ATTR_BATTERY_TYPE_AND_QUANTITY: self.coordinator.battery_type_and_quantity,
            ATTR_NOTE: self.coordinator.battery_note,
            ATTR_BATTERY_INCREASE_THRESHOLD: self.coordinator.battery_increased_threshold,
            ATTR_BATTERY_LOW: self.coordinator.battery_low,
            ATTR_BATTERY_LOW_THRESHOLD: self.coordinator.battery_low_threshold,
            ATTR_BATTERY_LAST_REPORTED: self.coordinator.last_reported,
            ATTR_BATTERY_LAST_REPORTED_LEVEL: self.coordinator.last_reported_level,
        }

        if self.enable_replaced:
            attrs[ATTR_BATTERY_LAST_REPLACED] = self.coordinator.last_replaced

        # Other attributes that should follow battery, attribute list is unsorted
        attrs[ATTR_DEVICE_ID] = self.coordinator.device_id or ""
        attrs[ATTR_SOURCE_ENTITY_ID] = self.coordinator.source_entity_id or ""
        attrs[ATTR_DEVICE_NAME] = self.coordinator.device_name

        super_attrs = super().extra_state_attributes
        if super_attrs:
            attrs.update(super_attrs)
        return attrs


class BatteryNotesBatteryPlusSensor(BatteryNotesBatteryPlusBaseSensor):
    """Represents a battery plus type sensor."""

    _wrapped_attributes = None

    def __init__(  # noqa: PLR0913
        self,
        hass: HomeAssistant,
        config_entry: BatteryNotesConfigEntry,
        subentry: ConfigSubentry,
        entity_description: BatteryNotesEntityDescription,
        coordinator: BatteryNotesSubentryCoordinator,
        unique_id: str,
        enable_replaced: bool,
        round_battery: bool,
    ) -> None:
        # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__(
            hass=hass,
            config_entry=config_entry,
            subentry=subentry,
            entity_description=entity_description,
            coordinator=coordinator,
            unique_id=unique_id,
            enable_replaced=enable_replaced,
            round_battery=round_battery,
        )

    async def async_state_changed_listener(
        self,
        event: Event[EventStateChangedData] | None = None,  # noqa: ARG002
    ) -> None:
        # pylint: disable=unused-argument
        """Handle child updates."""

        if not self.coordinator.wrapped_battery:
            return

        if (
            (
                wrapped_battery_state := self.hass.states.get(
                    self.coordinator.wrapped_battery.entity_id
                )
            )
            is None
            or wrapped_battery_state.state
            in [
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ]
            or not validate_is_float(wrapped_battery_state.state)
        ):
            _LOGGER.debug(
                "Sensor.py -> wrapped_battery_state: %s", wrapped_battery_state
            )
            if wrapped_battery_state:
                _LOGGER.debug(
                    "Sensor.py -> wrapped_battery_state.state: <%s>",
                    wrapped_battery_state.state,
                )
                _LOGGER.debug(
                    "Sensor.py -> validate_is_float: <%s>",
                    validate_is_float(wrapped_battery_state.state),
                )

            if self.coordinator.retain_state:
                return
            self._attr_native_value = None
            self._attr_available = False
            self._write_tracked_ha_state()
            return

        self.coordinator.current_battery_level = wrapped_battery_state.state

        await self.coordinator.async_request_refresh()

        self._attr_available = True
        self._attr_native_value = self.coordinator.rounded_battery_level
        self._wrapped_attributes = wrapped_battery_state.attributes

        self._write_tracked_ha_state()

    async def async_state_reported_listener(
        self,
        event: Event[EventStateReportedData] | None = None,  # noqa: ARG002
    ) -> None:
        """Handle child updates."""

        if not self.coordinator.wrapped_battery:
            return

        if (
            (
                wrapped_battery_state := self.hass.states.get(
                    self.coordinator.wrapped_battery.entity_id
                )
            )
            is None
            or wrapped_battery_state.state
            in [
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ]
            or not validate_is_float(wrapped_battery_state.state)
        ):
            if self.coordinator.retain_state:
                return
            self._attr_native_value = None
            self._attr_available = False
            self._write_tracked_ha_state()
            return

        # Don't update if battery level same and it's been < 1 hour, compare the raw
        # level as last_reported_level is rounded
        last_write = self.coordinator.last_wrapped_battery_state_write
        current_level = self.coordinator.current_battery_level
        if (
            last_write is not None
            and validate_is_float(current_level)
            and float(current_level) == float(wrapped_battery_state.state)
            and (dt_util.utcnow() - last_write).total_seconds()
            < STATE_WRITE_INTERVAL_SECONDS
        ):
            self._attr_available = True
            return

        self.coordinator.last_wrapped_battery_state_write = dt_util.utcnow()
        self.coordinator.current_battery_level = wrapped_battery_state.state

        self.coordinator.last_reported = dt_util.utcnow()

        _LOGGER.debug(
            "Entity id %s has been reported.",
            self.coordinator.wrapped_battery.entity_id,
        )

        await self.coordinator.async_request_refresh()

        self._attr_available = True
        self._attr_native_value = self.coordinator.rounded_battery_level
        self._wrapped_attributes = wrapped_battery_state.attributes

        self._write_tracked_ha_state()

    async def _register_entity_id_change_listener(
        self,
        entity_id: str,
        source_entity_id: str,
    ) -> None:
        """Listen for battery entity_id changes and update battery_plus."""

        async def _entity_rename_listener(
            event: Event[er.EventEntityRegistryUpdatedData],
        ) -> None:
            """Handle renaming of the entity."""

            new_entity_id = event.data["entity_id"]
            old_entity_id = event.data.get("old_entity_id", None)

            if not old_entity_id:
                return

            _LOGGER.debug(
                "Entity id has been changed, updating battery notes plus entity. old_id=%s, new_id=%s",
                old_entity_id,
                new_entity_id,
            )

            entity_registry = er.async_get(self.hass)
            if not entity_registry.async_get(entity_id):
                return

            new_wrapped_battery = entity_registry.async_get(new_entity_id)
            self.coordinator.wrapped_battery = new_wrapped_battery

            # Create a listener for the newly named battery entity
            if self.coordinator.wrapped_battery:
                self.async_on_remove(
                    async_track_state_change_event(
                        self.hass,
                        [self.coordinator.wrapped_battery.entity_id],
                        self.async_state_changed_listener,
                    )
                )

                self.async_on_remove(
                    async_track_state_report_event(
                        self.hass,
                        [self.coordinator.wrapped_battery.entity_id],
                        self.async_state_reported_listener,
                    )
                )

        @callback
        def _filter_entity_id(event_data: Mapping[str, Any]) -> bool:
            """Only dispatch the listener for update events concerning the source entity."""

            return (
                event_data["action"] == "update"
                and "old_entity_id" in event_data
                and event_data["old_entity_id"] == source_entity_id
            )

        self.async_on_remove(
            self.hass.bus.async_listen(
                EVENT_ENTITY_REGISTRY_UPDATED,
                _entity_rename_listener,
                event_filter=_filter_entity_id,
            )
        )

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        await super().async_added_to_hass()

        async def _async_state_changed_listener(
            event: Event[EventStateChangedData] | None = None,
        ) -> None:
            """Handle child updates."""
            await self.async_state_changed_listener(event)

        async def _async_state_reported_listener(
            event: Event[EventStateReportedData] | None = None,
        ) -> None:
            """Handle child updates."""
            await self.async_state_reported_listener(event)

        if self.coordinator.wrapped_battery:
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [self.coordinator.wrapped_battery.entity_id],
                    _async_state_changed_listener,
                )
            )

            self.async_on_remove(
                async_track_state_report_event(
                    self.hass,
                    [self.coordinator.wrapped_battery.entity_id],
                    _async_state_reported_listener,
                )
            )

            await self._register_entity_id_change_listener(
                self.entity_id,
                self.coordinator.wrapped_battery.entity_id,
            )

        # Call once on adding
        await _async_state_changed_listener()

        # Update entity options
        registry = er.async_get(self.hass)
        if (
            registry.async_get(self.entity_id) is not None
            and self.coordinator.wrapped_battery
        ):
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self.coordinator.wrapped_battery.entity_id},
            )

        if not self.coordinator.wrapped_battery:
            return

        domain_config = self.domain_config

        if domain_config.hide_battery:
            if (
                self.coordinator.wrapped_battery
                and not self.coordinator.wrapped_battery.hidden
            ):
                registry.async_update_entity(
                    self.coordinator.wrapped_battery.entity_id,
                    hidden_by=er.RegistryEntryHider.INTEGRATION,
                )
        elif (
            self.coordinator.wrapped_battery
            and self.coordinator.wrapped_battery.hidden_by
            == er.RegistryEntryHider.INTEGRATION
        ):
            registry.async_update_entity(
                self.coordinator.wrapped_battery.entity_id, hidden_by=None
            )

        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        _LOGGER.debug("Update from coordinator")
        battery_level = self.coordinator.rounded_battery_level

        if battery_level is not None:
            self._attr_native_value = battery_level

        self._write_tracked_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes of the battery type."""

        attrs: dict[str, Any] | None = None
        attrs = super().extra_state_attributes

        if self._wrapped_attributes:
            if attrs is None:
                attrs = {}
            attrs.update(self._wrapped_attributes)
        return attrs

    @property
    def native_value(self) -> StateType | Any | datetime:
        """Return the value reported by the sensor."""
        return self._attr_native_value


class BatteryNotesBatteryPlusTemplateSensor(
    TemplateTrackingMixin, BatteryNotesBatteryPlusBaseSensor
):
    """Represents a battery plus from template type sensor."""

    _state: float | None = None

    def __init__(  # noqa: PLR0913
        self,
        hass: HomeAssistant,
        config_entry: BatteryNotesConfigEntry,
        subentry: ConfigSubentry,
        entity_description: BatteryNotesEntityDescription,
        coordinator: BatteryNotesSubentryCoordinator,
        unique_id: str,
        enable_replaced: bool,
        round_battery: bool,
        battery_percentage_template: str,
    ) -> None:
        # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__(
            hass=hass,
            config_entry=config_entry,
            subentry=subentry,
            entity_description=entity_description,
            coordinator=coordinator,
            unique_id=unique_id,
            enable_replaced=enable_replaced,
            round_battery=round_battery,
        )
        self._init_template_tracking(battery_percentage_template)

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        await super().async_added_to_hass()

        self._async_start_template_tracking()

    @callback
    def _async_write_template_state(self) -> None:
        """Write the state through the battery plus write throttle."""
        self._write_tracked_ha_state()

    @callback
    def _update_state(self, result):
        try:
            state = None if isinstance(result, TemplateError) else float(result)
        except (ValueError, TypeError):
            state = None

        if state is None and self.coordinator.retain_state:
            # Reprocess recovery even if the valid percentage is unchanged
            self._state = None
            return

        self._attr_available = state is not None
        clamped_state = max(0, min(100, state)) if state is not None else state

        if clamped_state == self._state:
            return

        self._state = clamped_state
        self.coordinator.current_battery_level = clamped_state

        self._attr_available = clamped_state is not None
        self._attr_native_value = self.coordinator.rounded_battery_level

        _LOGGER.debug(
            "%s sensor battery_plus set to: %s via template",
            self.entity_id,
            clamped_state,
        )

    @property
    def native_value(self) -> StateType | Any | datetime:
        """Return the value reported by the sensor."""
        return self._attr_native_value

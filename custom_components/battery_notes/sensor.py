"""Sensor platform for battery_notes."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Event, HomeAssistant, callback, split_entity_id
from homeassistant.helpers import (
    config_validation as cv,
)
from homeassistant.helpers import (
    device_registry as dr,
)
from homeassistant.helpers import (
    entity_registry as er,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import (
    EVENT_ENTITY_REGISTRY_UPDATED,
)
from homeassistant.helpers.event import (
    EventStateChangedData,
    EventStateReportedData,
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
    async_track_state_report_event,
)
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from .common import utcnow_no_timezone, validate_is_float
from .const import (
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
    ATTR_SOURCE_ENTITY_ID,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import MY_KEY, BatteryNotesConfigEntry, BatteryNotesCoordinator
from .entity import (
    BatteryNotesEntityDescription,
)


@dataclass(frozen=True, kw_only=True)
class BatteryNotesSensorEntityDescription(
    BatteryNotesEntityDescription,
    SensorEntityDescription,
):
    """Describes Battery Notes sensor entity."""

    unique_id_suffix: str


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_SOURCE_ENTITY_ID): cv.string,
        vol.Required(CONF_BATTERY_TYPE): cv.string,
        vol.Required(CONF_BATTERY_QUANTITY): cv.positive_int,
    }
)

_LOGGER = logging.getLogger(__name__)


@callback
def async_add_to_device(hass: HomeAssistant, entry: BatteryNotesConfigEntry) -> str | None:
    """Add our config entry to the device."""
    device_registry = dr.async_get(hass)

    device_id = entry.data.get(CONF_DEVICE_ID)

    if device_id:
        if device_registry.async_get(device_id):
            device_registry.async_update_device(
                device_id, add_config_entry_id=entry.entry_id
            )
            return device_id
    return None


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: BatteryNotesConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    device_id = config_entry.data.get(CONF_DEVICE_ID, None)

    async def async_registry_updated(event: Event[er.EventEntityRegistryUpdatedData]) -> None:
        """Handle entity registry update."""
        data = event.data
        if data["action"] == "remove":
            await hass.config_entries.async_remove(config_entry.entry_id)

        if data["action"] != "update":
            return

        if "entity_id" in data["changes"]:
            # Entity_id replaced, reload the config entry
            await hass.config_entries.async_reload(config_entry.entry_id)

        if device_id and "device_id" in data["changes"]:
            # If the tracked battery note is no longer in the device, remove our config entry
            # from the device
            if (
                not (entity_entry := entity_registry.async_get(data["entity_id"]))
                or not device_registry.async_get(device_id)
                or entity_entry.device_id == device_id
            ):
                # No need to do any cleanup
                return

            device_registry.async_update_device(
                device_id, remove_config_entry_id=config_entry.entry_id
            )

    config_entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, config_entry.entry_id, async_registry_updated
        )
    )

    coordinator = config_entry.runtime_data.coordinator
    assert(coordinator)

    if not coordinator.fake_device:
        device_id = async_add_to_device(hass, config_entry)

        if not device_id:
            return

    await coordinator.async_refresh()

    domain_config = hass.data[MY_KEY]

    battery_plus_sensor_entity_description = BatteryNotesSensorEntityDescription(
        unique_id_suffix="_battery_plus",
        key="battery_plus",
        translation_key="battery_plus",
        device_class=SensorDeviceClass.BATTERY,
        suggested_display_precision=0 if domain_config.round_battery else 1,
    )

    type_sensor_entity_description = BatteryNotesSensorEntityDescription(
        unique_id_suffix="",  # battery_type has uniqueId set to entityId in V1, never add a suffix
        key="battery_type",
        translation_key="battery_type",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    last_replaced_sensor_entity_description = BatteryNotesSensorEntityDescription(
        unique_id_suffix="_battery_last_replaced",
        key="battery_last_replaced",
        translation_key="battery_last_replaced",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=domain_config.enable_replaced,
    )

    entities = [
        BatteryNotesTypeSensor(
            hass,
            config_entry,
            coordinator,
            type_sensor_entity_description,
            f"{config_entry.entry_id}{type_sensor_entity_description.unique_id_suffix}",
        ),
        BatteryNotesLastReplacedSensor(
            hass,
            config_entry,
            coordinator,
            last_replaced_sensor_entity_description,
            f"{config_entry.entry_id}{last_replaced_sensor_entity_description.unique_id_suffix}",
        ),
    ]

    if coordinator.wrapped_battery is not None:
        entities.append(
            BatteryNotesBatteryPlusSensor(
                hass,
                config_entry,
                coordinator,
                battery_plus_sensor_entity_description,
                f"{config_entry.entry_id}{battery_plus_sensor_entity_description.unique_id_suffix}",
                domain_config.enable_replaced,
                domain_config.round_battery,
            )
        )

    async_add_entities(entities)


async def async_setup_platform(
    hass: HomeAssistant,
) -> None:
    """Set up the battery note sensor."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)


class BatteryNotesBatteryPlusSensor(
    RestoreSensor, SensorEntity, CoordinatorEntity[BatteryNotesCoordinator]
):
    """Represents a battery plus type sensor."""

    _attr_should_poll = False
    _wrapped_attributes = None
    _unrecorded_attributes = frozenset(
        {
            ATTR_BATTERY_QUANTITY,
            ATTR_BATTERY_TYPE,
            ATTR_BATTERY_TYPE_AND_QUANTITY,
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

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesSensorEntityDescription,
        unique_id: str,
        enable_replaced: bool,
        round_battery: bool,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        device_registry = dr.async_get(hass)

        self.config_entry = config_entry
        self.coordinator = coordinator

        self._attr_has_entity_name = True

        if coordinator.source_entity_id and not coordinator.device_id:
            self._attr_translation_placeholders = {
                "device_name": coordinator.device_name + " "
            }
            self.entity_id = (
                f"sensor.{coordinator.device_name.lower()}_{description.key}"
            )
        elif coordinator.source_entity_id and coordinator.device_id:
            source_entity_domain, source_object_id = split_entity_id(
                coordinator.source_entity_id
            )
            self._attr_translation_placeholders = {
                "device_name": coordinator.source_entity_name + " "
            }
            self.entity_id = f"sensor.{source_object_id}_{description.key}"
        else:
            self._attr_translation_placeholders = {"device_name": ""}
            self.entity_id = (
                f"sensor.{coordinator.device_name.lower()}_{description.key}"
            )

        self.entity_description = description
        self._attr_unique_id = unique_id
        self.enable_replaced = enable_replaced
        self.round_battery = round_battery

        self._device_id = coordinator.device_id
        self._source_entity_id = coordinator.source_entity_id

        if coordinator.device_id and (
            device_entry := device_registry.async_get(coordinator.device_id)
        ):
            self._attr_device_info = DeviceInfo(
                connections=device_entry.connections,
                identifiers=device_entry.identifiers,
            )

        entity_category = (
            coordinator.wrapped_battery.entity_category if coordinator.wrapped_battery else None
        )

        self._attr_entity_category = entity_category
        self._attr_unique_id = unique_id

        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = PERCENTAGE

    @callback
    async def async_state_changed_listener(
        self, event: Event[EventStateChangedData] | None = None
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
            _LOGGER.debug("Sensor.py -> wrapped_battery_state: %s", wrapped_battery_state)
            if wrapped_battery_state:
                _LOGGER.debug("Sensor.py -> wrapped_battery_state.state: <%s>", wrapped_battery_state.state)
                _LOGGER.debug("Sensor.py -> validate_is_float: <%s>", validate_is_float(wrapped_battery_state.state))

            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        self.coordinator.current_battery_level = wrapped_battery_state.state

        await self.coordinator.async_request_refresh()

        self._attr_available = True
        self._attr_native_value = self.coordinator.rounded_battery_level
        self._wrapped_attributes = wrapped_battery_state.attributes

        self.async_write_ha_state()

    @callback
    async def async_state_reported_listener(
        self, event: Event[EventStateReportedData] | None = None
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
            self._attr_native_value = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        self.coordinator.current_battery_level = wrapped_battery_state.state

        await self.coordinator.async_request_refresh()

        self.coordinator.last_reported = utcnow_no_timezone()

        _LOGGER.debug(
            "Entity id %s has been reported.",
            self.coordinator.wrapped_battery.entity_id,
        )

        await self.coordinator.async_request_refresh()

        self._attr_available = True
        self._attr_native_value = self.coordinator.rounded_battery_level
        self._wrapped_attributes = wrapped_battery_state.attributes

        self.async_write_ha_state()

    async def _register_entity_id_change_listener(
        self,
        entity_id: str,
        source_entity_id: str,
    ) -> None:
        """Listen for battery entity_id changes and update battery_plus."""

        @callback
        async def _entity_rename_listener(event: Event[er.EventEntityRegistryUpdatedData]) -> None:
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

        self.hass.bus.async_listen(
            EVENT_ENTITY_REGISTRY_UPDATED,
            _entity_rename_listener,
            event_filter=_filter_entity_id,
        )

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        @callback
        async def _async_state_changed_listener(
            event: Event[EventStateChangedData] | None = None,
        ) -> None:
            """Handle child updates."""
            await self.async_state_changed_listener(event)

        @callback
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

        domain_config = self.hass.data[MY_KEY]

        if domain_config.hide_battery:
            if (
                self.coordinator.wrapped_battery
                and not self.coordinator.wrapped_battery.hidden
            ):
                registry.async_update_entity(
                    self.coordinator.wrapped_battery.entity_id,
                    hidden_by=er.RegistryEntryHider.INTEGRATION,
                )
        else:
            if (
                self.coordinator.wrapped_battery
                and self.coordinator.wrapped_battery.hidden_by
                == er.RegistryEntryHider.INTEGRATION
            ):
                registry.async_update_entity(
                    self.coordinator.wrapped_battery.entity_id, hidden_by=None
                )

        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        _LOGGER.debug("Update from coordinator")

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the state attributes of the battery type."""

        # Battery related attributes
        attrs = {
            ATTR_BATTERY_QUANTITY: self.coordinator.battery_quantity,
            ATTR_BATTERY_TYPE: self.coordinator.battery_type,
            ATTR_BATTERY_TYPE_AND_QUANTITY: self.coordinator.battery_type_and_quantity,
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
        if self._wrapped_attributes:
            attrs.update(self._wrapped_attributes)
        return attrs

    @property
    def native_value(self) -> StateType | Any | datetime:
        """Return the value reported by the sensor."""
        return self._attr_native_value


class BatteryNotesTypeSensor(RestoreSensor, SensorEntity):
    """Represents a battery note type sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription
    _unrecorded_attributes = frozenset({ATTR_BATTERY_QUANTITY, ATTR_BATTERY_TYPE})

    def __init__(
        self,
        hass,
        config_entry: ConfigEntry,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesSensorEntityDescription,
        unique_id: str,
    ) -> None:
        # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__()

        device_registry = dr.async_get(hass)

        self.coordinator = coordinator

        self._attr_has_entity_name = True

        if coordinator.source_entity_id and not coordinator.device_id:
            self._attr_translation_placeholders = {
                "device_name": coordinator.device_name + " "
            }
            self.entity_id = (
                f"sensor.{coordinator.device_name.lower()}_{description.key}"
            )
        elif coordinator.source_entity_id and coordinator.device_id:
            source_entity_domain, source_object_id = split_entity_id(
                coordinator.source_entity_id
            )
            self._attr_translation_placeholders = {
                "device_name": coordinator.source_entity_name + " "
            }
            self.entity_id = f"sensor.{source_object_id}_{description.key}"
        else:
            self._attr_translation_placeholders = {"device_name": ""}
            self.entity_id = (
                f"sensor.{coordinator.device_name.lower()}_{description.key}"
            )

        self.entity_description = description
        self._attr_unique_id = unique_id
        self._device_id = coordinator.device_id
        self._source_entity_id = coordinator.source_entity_id

        if coordinator.device_id and (
            device_entry := device_registry.async_get(coordinator.device_id)
        ):
            self._attr_device_info = DeviceInfo(
                connections=device_entry.connections,
                identifiers=device_entry.identifiers,
            )

        self._battery_type = coordinator.battery_type
        self._battery_quantity = coordinator.battery_quantity

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_sensor_data()
        if state:
            self._attr_native_value = state.native_value

        # Update entity options
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
        }

        super_attrs = super().extra_state_attributes
        if super_attrs:
            attrs.update(super_attrs)
        return attrs


class BatteryNotesLastReplacedSensor(
    SensorEntity, CoordinatorEntity[BatteryNotesCoordinator]
):
    """Represents a battery note sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription

    def __init__(
        self,
        hass,
        config_entry: ConfigEntry,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesSensorEntityDescription,
        unique_id: str,
    ) -> None:
        # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__(coordinator)

        self.coordinator = coordinator

        self._attr_has_entity_name = True

        if coordinator.source_entity_id and not coordinator.device_id:
            self._attr_translation_placeholders = {
                "device_name": coordinator.device_name + " "
            }
            self.entity_id = (
                f"sensor.{coordinator.device_name.lower()}_{description.key}"
            )
        elif coordinator.source_entity_id and coordinator.device_id:
            source_entity_domain, source_object_id = split_entity_id(
                coordinator.source_entity_id
            )
            self._attr_translation_placeholders = {
                "device_name": coordinator.source_entity_name + " "
            }
            self.entity_id = f"sensor.{source_object_id}_{description.key}"
        else:
            self._attr_translation_placeholders = {"device_name": ""}
            self.entity_id = (
                f"sensor.{coordinator.device_name.lower()}_{description.key}"
            )

        self._attr_device_class = description.device_class
        self._attr_unique_id = unique_id
        self._device_id = coordinator.device_id
        self._source_entity_id = coordinator.source_entity_id
        self.entity_description = description
        self._native_value: datetime | None = None

        self._set_native_value(log_on_error=False)

        device_registry = dr.async_get(hass)

        if coordinator.device_id and (
            device_entry := device_registry.async_get(coordinator.device_id)
        ):
            self._attr_device_info = DeviceInfo(
                connections=device_entry.connections,
                identifiers=device_entry.identifiers,
            )

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()

    def _set_native_value(self, log_on_error=True):
        # pylint: disable=unused-argument

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

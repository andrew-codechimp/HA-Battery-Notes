"""Sensor platform for battery_notes."""
from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
import voluptuous as vol
from contextlib import suppress

from homeassistant.components.homeassistant import exposed_entities
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    RestoreSensor,
    Entity,
)
# from homeassistant.components import state_changes_during_period
from homeassistant.components.recorder import get_instance, history
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ENTITY_ID
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
    async_track_entity_registry_updated_event,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import EventType

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN


from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICE_ID,
    DEVICE_CLASS_BATTERY,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    PERCENTAGE,
)

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_BATTERY_TYPE,
    CONF_BATTERY_QUANTITY,
    DATA,
    DATA_COORDINATOR,
    DATA_STORE,
    LAST_REPLACED,
    DOMAIN_CONFIG,
    CONF_ENABLE_REPLACED,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_TYPE,
    ATTR_DATE_TIME_REPLACED,
)

from .coordinator import BatteryNotesCoordinator

from .entity import (
    BatteryNotesEntityDescription,
)


@dataclass
class BatteryNotesSensorEntityDescription(
    BatteryNotesEntityDescription,
    SensorEntityDescription,
):
    """Describes Battery Notes sensor entity."""

    unique_id_suffix: str


PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_BATTERY_TYPE): cv.string,
        vol.Required(CONF_BATTERY_QUANTITY): cv.positive_int,
    }
)


@callback
def async_add_to_device(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Add our config entry to the device."""
    device_registry = dr.async_get(hass)

    device_id = entry.data.get(CONF_DEVICE_ID)
    device_registry.async_update_device(device_id, add_config_entry_id=entry.entry_id)

    return device_id


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    async def async_registry_updated(event: Event) -> None:
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
                not (entity_entry := entity_registry.async_get(data[CONF_ENTITY_ID]))
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

    device_id = async_add_to_device(hass, config_entry)

    coordinator = hass.data[DOMAIN][DATA].devices[config_entry.entry_id].coordinator

    await coordinator.async_refresh()

    enable_replaced = True
    if DOMAIN_CONFIG in hass.data[DOMAIN]:
        domain_config: dict = hass.data[DOMAIN][DOMAIN_CONFIG]
        enable_replaced = domain_config.get(CONF_ENABLE_REPLACED, True)

    noted_battery_sensor_entity_description = BatteryNotesSensorEntityDescription(
        unique_id_suffix="_battery_noted",
        key="battery_noted",
        translation_key="battery_noted",
        device_class=SensorDeviceClass.BATTERY,
    )

    type_sensor_entity_description = BatteryNotesSensorEntityDescription(
        unique_id_suffix="",  # battery_type has uniqueId set to entityId in V1, never add a suffix
        key="battery_type",
        translation_key="battery_type",
        icon="mdi:battery-unknown",
        entity_category=EntityCategory.DIAGNOSTIC,
    )

    last_replaced_sensor_entity_description = BatteryNotesSensorEntityDescription(
        unique_id_suffix="_battery_last_replaced",
        key="battery_last_replaced",
        translation_key="battery_last_replaced",
        icon="mdi:battery-clock",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=enable_replaced,
    )

    entities = [
        BatteryNotesBatteryNotedSensor(
            hass,
            config_entry,
            coordinator,
            noted_battery_sensor_entity_description,
            f"{config_entry.entry_id}{noted_battery_sensor_entity_description.unique_id_suffix}",
        ),
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

    async_add_entities(entities)

    await coordinator.async_config_entry_first_refresh()


async def async_setup_platform(
    hass: HomeAssistant,
) -> None:
    """Set up the battery note sensor."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

class BatteryNotesBatteryNotedSensor(SensorEntity):
    """Represents a noted battery type sensor."""

    _attr_should_poll = False
    _is_new_entity: bool
    _value: None
    _wrapped_attributes: None

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesSensorEntityDescription,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()

        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)

        self.config_entry = config_entry
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = unique_id

        if coordinator.device_id and (device := device_registry.async_get(coordinator.device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )

            self.entity_id = f"sensor.{device.name}_{description.key}"

        # Find the battery for the device
        wrapped_battery = None

        for entity in entity_registry.entities.values():
            if not entity.device_id or entity.device_id != coordinator.device_id:
                continue
            if not entity.domain or not entity.domain in {BINARY_SENSOR_DOMAIN, SENSOR_DOMAIN}:
                continue
            if not entity.platform or entity.platform == DOMAIN:
                continue
            device_class = entity.device_class or entity.original_device_class
            if not device_class == DEVICE_CLASS_BATTERY:
                continue

            wrapped_battery = entity_registry.async_get(entity.entity_id)

        entity_category = wrapped_battery.entity_category if wrapped_battery else None
        has_entity_name = wrapped_battery.has_entity_name if wrapped_battery else False

        name: str | None = config_entry.title
        if wrapped_battery:
            name = wrapped_battery.original_name + "+"

        self._device_id = coordinator.device_id
        if coordinator.device_id and (device := device_registry.async_get(coordinator.device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )
        self._attr_entity_category = entity_category
        self._attr_has_entity_name = has_entity_name
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._battery_entity_id = wrapped_battery.entity_id if wrapped_battery else None

        self._attr_device_class = SensorDeviceClass.BATTERY
        self._attr_state_class = SensorDeviceClass.BATTERY
        self._attr_native_unit_of_measurement = PERCENTAGE


        self._is_new_entity = (
            entity_registry.async_get_entity_id(DOMAIN, DOMAIN, unique_id) is None
        )

    @callback
    def async_state_changed_listener(
        self, event: EventType[EventStateChangedData] | None = None
    ) -> None:
        """Handle child updates."""
        updated = False

        if (
            state := self.hass.states.get(self._battery_entity_id)
        ) is None or state.state == STATE_UNAVAILABLE:
            self._attr_available = False
            return

        print(state)

        self._value = state.state
        self._wrapped_attributes = state.attributes

        self._attr_available = True

        updated = True


        # history_list = history.state_changes_during_period(
        #     self.hass,
        #     datetime.datetime.now() - datetime.timedelta(hours=1),
        #     entity_id=self._battery_entity_id,
        #     no_attributes=True,
        # )
        # for state in history_list.get(self._battery_entity_id, []):
        #     # filter out all None, NaN and "unknown" states
        #     # only keep real values
        #     with suppress(ValueError):
        #         print(int(state.state))

        if updated:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        @callback
        def _async_state_changed_listener(
            event: EventType[EventStateChangedData] | None = None,
        ) -> None:
            """Handle child updates."""
            self.async_state_changed_listener(event)

        self.async_on_remove(
            async_track_state_change_event(
                self.hass, [self._battery_entity_id], _async_state_changed_listener
            )
        )

        # Call once on adding
        _async_state_changed_listener()

        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._battery_entity_id},
            )

        if not self._is_new_entity or not (
            wrapped_battery := registry.async_get(self._battery_entity_id)
        ):
            return

        def copy_custom_name(wrapped_battery: er.RegistryEntry) -> None:
            """Copy the name set by user from the wrapped entity."""
            if wrapped_battery.name is None:
                return
            registry.async_update_entity(self.entity_id, name=wrapped_battery.name)

        def copy_expose_settings() -> None:
            """Copy assistant expose settings from the wrapped entity.

            Also unexpose the wrapped entity if exposed.
            """
            expose_settings = exposed_entities.async_get_entity_settings(
                self.hass, self._battery_entity_id
            )
            for assistant, settings in expose_settings.items():
                if (should_expose := settings.get("should_expose")) is None:
                    continue
                exposed_entities.async_expose_entity(
                    self.hass, assistant, self.entity_id, should_expose
                )
                exposed_entities.async_expose_entity(
                    self.hass, assistant, self._battery_entity_id, False
                )

        copy_custom_name(wrapped_battery)
        copy_expose_settings()

    # @callback
    # def _handle_coordinator_update(self) -> None:
    #     """Handle updated data from the coordinator."""

    #     self.async_schedule_update_ha_state(force_refresh =True)

    @property
    def native_value(self) -> int | None:
        """ Return the state of the sensor. """
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes of the battery type."""

        attrs = {
            ATTR_BATTERY_QUANTITY: self.coordinator.battery_quantity,
            ATTR_BATTERY_TYPE: self.coordinator.battery_type,
            ATTR_DATE_TIME_REPLACED: self.coordinator.last_replaced,
        }

        super_attrs = super().extra_state_attributes
        if super_attrs:
            attrs.update(super_attrs)
        if self._wrapped_attributes:
            attrs.update(self._wrapped_attributes)
        return attrs

class BatteryNotesTypeSensor(RestoreSensor, SensorEntity):
    """Represents a battery note type sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription

    def __init__(
        self,
        hass,
        config_entry: ConfigEntry,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesSensorEntityDescription,
        unique_id: str,
    ) -> None: # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__()

        device_registry = dr.async_get(hass)

        self.coordinator = coordinator
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = unique_id
        self._device_id = coordinator.device_id

        if coordinator.device_id and (device := device_registry.async_get(coordinator.device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )

            self.entity_id = f"sensor.{device.name}_{description.key}"

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

        if self._battery_quantity and int(self._battery_quantity) > 1:
            return str(self._battery_quantity) + "x " + self._battery_type
        return self._battery_type

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes of the battery type."""

        attrs = {
            ATTR_BATTERY_QUANTITY: self.coordinator.battery_quantity,
            ATTR_BATTERY_TYPE: self.coordinator.battery_type,
        }

        super_attrs = super().extra_state_attributes
        if super_attrs:
            attrs.update(super_attrs)
        return attrs


class BatteryNotesLastReplacedSensor(SensorEntity, CoordinatorEntity):
    """Represents a battery note sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription
    _battery_entity_id = None

    def __init__(
        self,
        hass,
        config_entry: ConfigEntry,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesSensorEntityDescription,
        unique_id: str,
    ) -> None: # pylint: disable=unused-argument
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_class = description.device_class
        self._attr_has_entity_name = True
        self._attr_unique_id = unique_id
        self._device_id = coordinator.device_id
        self.entity_description = description
        self._native_value = None

        self._set_native_value(log_on_error=False)

        device_registry = dr.async_get(hass)

        if coordinator.device_id and (device := device_registry.async_get(coordinator.device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )

            self.entity_id = f"sensor.{device.name}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()

    def _set_native_value(self, log_on_error=True):  # pylint: disable=unused-argument
        device_entry = self.coordinator.store.async_get_device(self._device_id)
        if device_entry:
            if LAST_REPLACED in device_entry:
                last_replaced_date = datetime.fromisoformat(
                    str(device_entry[LAST_REPLACED]) + "+00:00"
                )
                self._native_value = last_replaced_date

                return True
        return False

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        device_entry = self.coordinator.store.async_get_device(self._device_id)
        if device_entry:
            if LAST_REPLACED in device_entry:
                last_replaced_date = datetime.fromisoformat(
                    str(device_entry[LAST_REPLACED]) + "+00:00"
                )
                self._native_value = last_replaced_date

                self.async_write_ha_state()

    @property
    def native_value(self) -> datetime | None:
        """Return the native value of the sensor."""
        return self._native_value

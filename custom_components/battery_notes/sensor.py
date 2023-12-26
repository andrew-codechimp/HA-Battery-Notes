"""Sensor platform for battery_notes."""
from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
import voluptuous as vol
import logging

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    RestoreSensor,
)
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
    async_track_state_change_event,
    async_track_entity_registry_updated_event,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from homeassistant.helpers.reload import async_setup_reload_service

from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICE_ID,
)

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_BATTERY_TYPE,
    DATA_UPDATE_COORDINATOR,
    DATA_COORDINATOR,
    LAST_REPLACED,
)

from .library_coordinator import BatteryNotesLibraryUpdateCoordinator
from .coordinator import BatteryNotesCoordinator

from .entity import (
    BatteryNotesEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class BatteryNotesSensorEntityDescription(
    BatteryNotesEntityDescription,
    SensorEntityDescription,
):
    """Describes Battery Notes sensor entity."""

    unique_id_suffix: str


typeSensorEntityDescription = BatteryNotesSensorEntityDescription(
    unique_id_suffix="",  # battery_type has uniqueId set to entityId in V1, never add a suffix
    key="battery_type",
    translation_key="battery_type",
    icon="mdi:battery-unknown",
    entity_category=EntityCategory.DIAGNOSTIC,
)

lastReplacedSensorEntityDescription = BatteryNotesSensorEntityDescription(
    unique_id_suffix="_battery_last_replaced",
    key="battery_last_replaced",
    translation_key="battery_last_replaced",
    icon="mdi:battery-clock",
    entity_category=EntityCategory.DIAGNOSTIC,
    device_class=SensorDeviceClass.TIMESTAMP,
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Required(CONF_DEVICE_ID): cv.string,
        vol.Required(CONF_BATTERY_TYPE): cv.string,
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

    device_id = config_entry.data.get(CONF_DEVICE_ID)
    battery_type = config_entry.data.get(CONF_BATTERY_TYPE)

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

    library_coordinator = hass.data[DOMAIN][DATA_UPDATE_COORDINATOR]
    coordinator = hass.data[DOMAIN][DATA_COORDINATOR]

    entities = [
        BatteryNotesTypeSensor(
            hass,
            library_coordinator,
            typeSensorEntityDescription,
            device_id,
            f"{config_entry.entry_id}{typeSensorEntityDescription.unique_id_suffix}",
            battery_type,
        ),
        BatteryNotesLastReplacedSensor(
            hass,
            coordinator,
            lastReplacedSensorEntityDescription,
            device_id,
            f"{config_entry.entry_id}{lastReplacedSensorEntityDescription.unique_id_suffix}",
        ),
    ]

    async_add_entities(entities)

    await coordinator.async_config_entry_first_refresh()


async def async_setup_platform(
    hass: HomeAssistant,
) -> None:
    """Set up the battery note sensor."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)


class BatteryNotesSensor(RestoreSensor, SensorEntity, CoordinatorEntity):
    """Represents a battery note sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription

    def __init__(
        self,
        hass,
        coordinator: BatteryNotesLibraryUpdateCoordinator,
        description: BatteryNotesSensorEntityDescription,
        device_id: str,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)

        device_registry = dr.async_get(hass)

        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = unique_id
        self._device_id = device_id

        if device_id and (device := device_registry.async_get(device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()
        state = await self.async_get_last_sensor_data()
        if state:
            self._attr_native_value = state.native_value

        self.async_on_remove(
            async_track_state_change_event(
                self.hass,
                [self._attr_unique_id],
                self._async_battery_note_state_replaced_listener,
            )
        )

        # Call once on adding
        self._async_battery_note_state_replaced_listener()

        # Update entity options
        registry = er.async_get(self.hass)
        if registry.async_get(self.entity_id) is not None:
            registry.async_update_entity_options(
                self.entity_id,
                DOMAIN,
                {"entity_id": self._attr_unique_id},
            )

    @callback
    def _async_battery_note_state_replaced_listener(self) -> None:
        """Handle the sensor state changes."""

        self.async_write_ha_state()
        self.async_schedule_update_ha_state(True)


class BatteryNotesTypeSensor(BatteryNotesSensor):
    """Represents a battery note sensor."""

    entity_description: BatteryNotesSensorEntityDescription

    def __init__(
        self,
        hass,
        coordinator: BatteryNotesLibraryUpdateCoordinator,
        description: BatteryNotesSensorEntityDescription,
        device_id: str,
        unique_id: str,
        battery_type: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass, coordinator, description, device_id, unique_id)

        self._battery_type = battery_type

    @property
    def native_value(self) -> str:
        """Return the native value of the sensor."""

        return self._battery_type

    @callback
    def _async_battery_type_state_replaced_listener(self) -> None:
        """Handle the sensor state changes."""
        self.async_write_ha_state()
        self.async_schedule_update_ha_state(True)


class BatteryNotesLastReplacedSensor(SensorEntity, CoordinatorEntity):
    """Represents a battery note sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription

    def __init__(
        self,
        hass,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesSensorEntityDescription,
        device_id: str,
        unique_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_device_class = description.device_class
        self._attr_has_entity_name = True
        self._attr_unique_id = unique_id
        self._device_id = device_id
        self.entity_description = description
        self._native_value = None

        self._set_native_value(log_on_error=False)

        device_registry = dr.async_get(hass)

        if device_id and (device := device_registry.async_get(device_id)):
            self._attr_device_info = DeviceInfo(
                connections=device.connections,
                identifiers=device.identifiers,
            )

    def _set_native_value(self, log_on_error=True):
        device_entry = self.coordinator.store.async_get_device(self._device_id)
        if device_entry:
            if LAST_REPLACED in device_entry:
                last_replaced_date = datetime.fromisoformat(
                    str(device_entry[LAST_REPLACED]) + "+00:00"
                )
                self._native_value = last_replaced_date

                return True
        return False

    # async def async_added_to_hass(self) -> None:
    #     """Handle added to Hass."""
    #     await super().async_added_to_hass()

    #     self.async_on_remove(
    #         async_track_state_change_event(
    #             self.hass,
    #             [self._attr_unique_id],
    #             self._async_battery_note_state_replaced_listener,
    #         )
    #     )

    #     # Update entity options
    #     registry = er.async_get(self.hass)
    #     if registry.async_get(self.entity_id) is not None:
    #         registry.async_update_entity_options(
    #             self.entity_id,
    #             DOMAIN,
    #             {"entity_id": self._attr_unique_id},
    #         )

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

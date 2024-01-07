"""Sensor platform for battery_notes."""
from __future__ import annotations

from datetime import datetime
from dataclasses import dataclass
import voluptuous as vol
import re
from contextlib import suppress

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    RestoreSensor,
)
from homeassistant.components import state_changes_during_period
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
    async_track_entity_registry_updated_event,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.reload import async_setup_reload_service
from homeassistant.helpers.event import async_track_state_change_event

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN

from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICE_ID,
    DEVICE_CLASS_BATTERY,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_BATTERY_TYPE,
    DATA_COORDINATOR,
    LAST_REPLACED,
    DOMAIN_CONFIG,
    CONF_ENABLE_REPLACED,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_TYPE,
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

    coordinator: BatteryNotesCoordinator = hass.data[DOMAIN][DATA_COORDINATOR]

    enable_replaced = True
    if DOMAIN_CONFIG in hass.data[DOMAIN]:
        domain_config: dict = hass.data[DOMAIN][DOMAIN_CONFIG]
        enable_replaced = domain_config.get(CONF_ENABLE_REPLACED, True)

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
        BatteryNotesTypeSensor(
            hass,
            type_sensor_entity_description,
            device_id,
            f"{config_entry.entry_id}{type_sensor_entity_description.unique_id_suffix}",
            battery_type,
        ),
        BatteryNotesLastReplacedSensor(
            hass,
            coordinator,
            last_replaced_sensor_entity_description,
            device_id,
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


class BatteryNotesTypeSensor(RestoreSensor, SensorEntity):
    """Represents a battery note type sensor."""

    _attr_should_poll = False
    entity_description: BatteryNotesSensorEntityDescription

    def __init__(
        self,
        hass,
        description: BatteryNotesSensorEntityDescription,
        device_id: str,
        unique_id: str,
        battery_type: str | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__()

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

            self.entity_id = f"sensor.{device.name}_{description.key}"

        self._battery_type = battery_type

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

        return self._battery_type

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes of the battery type."""

        matches: re.Match = re.search(
            r"^(\d+)(?=x)(?:x\s)(\w+$)|([\s\S]+)", self._battery_type
        )
        if matches:
            _qty = matches.group(1) if matches.group(1) is not None else "1"
            _type = (
                matches.group(2) if matches.group(2) is not None else matches.group(3)
            )
        else:
            _qty = 1
            _type = self._battery_type

        attrs = {
            ATTR_BATTERY_QUANTITY: _qty,
            ATTR_BATTERY_TYPE: _type,
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

            self.entity_id = f"sensor.{device.name}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""
        await super().async_added_to_hass()

        if (entry := self.registry_entry) and entry.disabled_by is None:
            self._async_listen_to_battery()

    async def _async_listen_to_battery(self) -> None:
        entity_registry = er.async_get(self.hass)

        # domain_device_classes = {
        #         ("input_number", DEVICE_CLASS_BATTERY),
        #         (BINARY_SENSOR_DOMAIN, DEVICE_CLASS_BATTERY),
        #         (SENSOR_DOMAIN, DEVICE_CLASS_BATTERY),
        #     }
        #
        # lookup: dict[str, dict[tuple[str, str | None], str]] = {}
        # for entity in entity_registry.entities.values():
        #     # if not entity.device_id:
        #     #     continue
        #     device_class = entity.device_class or entity.original_device_class
        #     domain_device_class = (entity.domain, device_class)
        #     if domain_device_class not in domain_device_classes:
        #         continue
        #     if entity.entity_id not in lookup:
        #         lookup[entity.entity_id] = {domain_device_class: entity.entity_id}
        #     else:
        #         lookup[entity.entity_id][domain_device_class] = entity.entity_id
        # print(lookup)

        # Get all entities that have a device and have specific domain/class
        device_lookup = entity_registry.async_get_device_class_lookup(
            {
                (BINARY_SENSOR_DOMAIN, DEVICE_CLASS_BATTERY),
                (SENSOR_DOMAIN, DEVICE_CLASS_BATTERY),
                (SENSOR_DOMAIN, "timestamp"),
            }
        )

        # For those that are related to this sensor's device, start listening for state changes
        if self._device_id in device_lookup:
            if (SENSOR_DOMAIN, "timestamp") in device_lookup[self._device_id]:
                self._battery_entity_id = device_lookup[self._device_id].get((SENSOR_DOMAIN, "timestamp"))
            else:
                self._battery_entity_id = device_lookup[self._device_id].get((BINARY_SENSOR_DOMAIN, "timestamp"))

            if self._battery_entity_id:
                print(self._battery_entity_id)

                self.async_on_remove(
                    async_track_state_change_event(
                            self.hass, self._battery_entity_id, self._async_state_listener
                    )
                )

    async def _async_state_listener(self, event: Event):

        state = event.data.get("new_state")
        if state is None or state.state in (STATE_UNKNOWN, "", STATE_UNAVAILABLE):
            return

        history_list = history.state_changes_during_period(
            self.hass,
            datetime.datetime.now() - datetime.timedelta(hours=1),
            entity_id=self._battery_entity_id,
            no_attributes=True,
        )
        for state in history_list.get(self._battery_entity_id, []):
            # filter out all None, NaN and "unknown" states
            # only keep real values
            with suppress(ValueError):
                print(int(state.state))

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
    def _async_state_listener(self, event: Event) -> None:
        """ Listen for sensor state changes. """
        updated = False

        # event.data
        # updated = True

        if updated:
            self.async_write_ha_state()

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

"""Define services for the Battery Notes integration."""

import logging
from datetime import datetime

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_BATTERY_LAST_REPORTED,
    ATTR_BATTERY_LAST_REPORTED_DAYS,
    ATTR_BATTERY_LAST_REPORTED_LEVEL,
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_QUANTITY,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_PREVIOUS_BATTERY_LEVEL,
    ATTR_SOURCE_ENTITY_ID,
    DATA,
    DOMAIN,
    EVENT_BATTERY_NOT_REPORTED,
    EVENT_BATTERY_REPLACED,
    EVENT_BATTERY_THRESHOLD,
    SERVICE_BATTERY_REPLACED,
    SERVICE_BATTERY_REPLACED_SCHEMA,
    SERVICE_CHECK_BATTERY_LAST_REPORTED,
    SERVICE_CHECK_BATTERY_LAST_REPORTED_SCHEMA,
    SERVICE_CHECK_BATTERY_LOW,
    SERVICE_DATA_DATE_TIME_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPORTED,
)
from .device import BatteryNotesDevice

_LOGGER = logging.getLogger(__name__)

def setup_services(hass: HomeAssistant) -> None:
    """Set up the services used by battery notes component."""

    async def handle_battery_replaced(call: ServiceCall) -> ServiceResponse:
        """Handle the service call."""
        device_id = call.data.get(ATTR_DEVICE_ID, "")
        source_entity_id = call.data.get(ATTR_SOURCE_ENTITY_ID, "")
        datetime_replaced_entry = call.data.get(SERVICE_DATA_DATE_TIME_REPLACED)

        if datetime_replaced_entry:
            datetime_replaced = dt_util.as_utc(datetime_replaced_entry).replace(
                tzinfo=None
            )
        else:
            datetime_replaced = datetime.utcnow()

        entity_registry = er.async_get(hass)
        device_registry = dr.async_get(hass)

        if source_entity_id:
            source_entity_entry = entity_registry.async_get(source_entity_id)
            if not source_entity_entry:
                _LOGGER.error(
                    "Entity %s not found",
                    source_entity_id,
                )
                return None

            # entity_id is the associated entity, now need to find the config entry for battery notes
            for config_entry in hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("source_entity_id") == source_entity_id:
                    config_entry_id = config_entry.entry_id

                    coordinator = (
                        hass.data[DOMAIN][DATA].devices[config_entry_id].coordinator
                    )

                    coordinator.last_replaced =datetime_replaced
                    await coordinator.async_request_refresh()

                    _LOGGER.debug(
                        "Entity %s battery replaced on %s",
                        source_entity_id,
                        str(datetime_replaced),
                    )

                    hass.bus.async_fire(
                        EVENT_BATTERY_REPLACED,
                        {
                            ATTR_DEVICE_ID: coordinator.device_id or "",
                            ATTR_SOURCE_ENTITY_ID: coordinator.source_entity_id
                            or "",
                            ATTR_DEVICE_NAME: coordinator.device_name,
                            ATTR_BATTERY_TYPE_AND_QUANTITY: coordinator.battery_type_and_quantity,
                            ATTR_BATTERY_TYPE: coordinator.battery_type,
                            ATTR_BATTERY_QUANTITY: coordinator.battery_quantity,
                        },
                    )

                    _LOGGER.debug(
                        "Raised event battery replaced %s",
                        coordinator.device_id,
                    )

                    return None

            _LOGGER.error("Entity %s not configured in Battery Notes", source_entity_id)

        else:
            device_entry = device_registry.async_get(device_id)
            if not device_entry:
                _LOGGER.error(
                    "Device %s not found",
                    device_id,
                )
                return None

            for entry_id in device_entry.config_entries:
                if (
                    entry := hass.config_entries.async_get_entry(entry_id)
                ) and entry.domain == DOMAIN:
                    coordinator = (
                        hass.data[DOMAIN][DATA].devices[entry.entry_id].coordinator
                    )

                    coordinator.last_replaced =datetime_replaced

                    await coordinator.async_request_refresh()

                    _LOGGER.debug(
                        "Device %s battery replaced on %s",
                        device_id,
                        str(datetime_replaced),
                    )

                    hass.bus.async_fire(
                        EVENT_BATTERY_REPLACED,
                        {
                            ATTR_DEVICE_ID: coordinator.device_id or "",
                            ATTR_SOURCE_ENTITY_ID: coordinator.source_entity_id
                            or "",
                            ATTR_DEVICE_NAME: coordinator.device_name,
                            ATTR_BATTERY_TYPE_AND_QUANTITY: coordinator.battery_type_and_quantity,
                            ATTR_BATTERY_TYPE: coordinator.battery_type,
                            ATTR_BATTERY_QUANTITY: coordinator.battery_quantity,
                        },
                    )

                    _LOGGER.debug(
                        "Raised event battery replaced %s",
                        coordinator.device_id,
                    )

                    # Found and dealt with, exit
                    return None

            _LOGGER.error(
                "Device %s not configured in Battery Notes",
                device_id,
            )
            return None


    async def handle_battery_last_reported(call: ServiceCall) -> ServiceResponse:
        """Handle the service call."""
        days_last_reported = call.data.get(SERVICE_DATA_DAYS_LAST_REPORTED)

        device: BatteryNotesDevice
        for device in hass.data[DOMAIN][DATA].devices.values():
            if device.coordinator.wrapped_battery and device.coordinator.last_reported:
                time_since_lastreported = (
                    datetime.fromisoformat(str(datetime.utcnow()) + "+00:00")
                    - device.coordinator.last_reported
                )

                if time_since_lastreported.days > days_last_reported:
                    hass.bus.async_fire(
                        EVENT_BATTERY_NOT_REPORTED,
                        {
                            ATTR_DEVICE_ID: device.coordinator.device_id or "",
                            ATTR_SOURCE_ENTITY_ID: device.coordinator.source_entity_id
                            or "",
                            ATTR_DEVICE_NAME: device.coordinator.device_name,
                            ATTR_BATTERY_TYPE_AND_QUANTITY: device.coordinator.battery_type_and_quantity,
                            ATTR_BATTERY_TYPE: device.coordinator.battery_type,
                            ATTR_BATTERY_QUANTITY: device.coordinator.battery_quantity,
                            ATTR_BATTERY_LAST_REPORTED: device.coordinator.last_reported,
                            ATTR_BATTERY_LAST_REPORTED_DAYS: time_since_lastreported.days,
                            ATTR_BATTERY_LAST_REPORTED_LEVEL: device.coordinator.last_reported_level,
                        },
                    )

                    _LOGGER.debug(
                        "Raised event device %s not reported since %s",
                        device.coordinator.device_id,
                        str(device.coordinator.last_reported),
                    )
        return None

    async def handle_battery_low(call: ServiceCall) -> ServiceResponse:
        """Handle the service call."""

        device: BatteryNotesDevice
        for device in hass.data[DOMAIN][DATA].devices.values():
            if device.coordinator.battery_low is True:
                hass.bus.async_fire(
                    EVENT_BATTERY_THRESHOLD,
                    {
                        ATTR_DEVICE_ID: device.coordinator.device_id or "",
                        ATTR_DEVICE_NAME: device.coordinator.device_name,
                        ATTR_SOURCE_ENTITY_ID: device.coordinator.source_entity_id
                        or "",
                        ATTR_BATTERY_LOW: device.coordinator.battery_low,
                        ATTR_BATTERY_TYPE_AND_QUANTITY: device.coordinator.battery_type_and_quantity,
                        ATTR_BATTERY_TYPE: device.coordinator.battery_type,
                        ATTR_BATTERY_QUANTITY: device.coordinator.battery_quantity,
                        ATTR_BATTERY_LEVEL: device.coordinator.rounded_battery_level,
                        ATTR_PREVIOUS_BATTERY_LEVEL: device.coordinator.rounded_previous_battery_level,
                        ATTR_BATTERY_THRESHOLD_REMINDER: True,
                    },
                )

                _LOGGER.debug(
                    "Raised event device %s battery low",
                    device.coordinator.device_id,
                )
        return None

    hass.services.async_register(
        DOMAIN,
        SERVICE_BATTERY_REPLACED,
        handle_battery_replaced,
        schema=SERVICE_BATTERY_REPLACED_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LAST_REPORTED,
        handle_battery_last_reported,
        schema=SERVICE_CHECK_BATTERY_LAST_REPORTED_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LOW,
        handle_battery_low,
    )

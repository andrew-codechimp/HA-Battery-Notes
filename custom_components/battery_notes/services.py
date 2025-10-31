"""Define services for the Battery Notes integration."""

import logging
from typing import cast
from datetime import datetime

from homeassistant.core import (
    ServiceCall,
    HomeAssistant,
    ServiceResponse,
    callback,
)
from homeassistant.util import dt as dt_util
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN,
    ATTR_DEVICE_ID,
    ATTR_BATTERY_LOW,
    ATTR_DEVICE_NAME,
    ATTR_BATTERY_TYPE,
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY_QUANTITY,
    ATTR_SOURCE_ENTITY_ID,
    EVENT_BATTERY_REPLACED,
    EVENT_BATTERY_THRESHOLD,
    SERVICE_BATTERY_REPLACED,
    SERVICE_CHECK_BATTERY_LOW,
    ATTR_BATTERY_LAST_REPLACED,
    ATTR_BATTERY_LAST_REPORTED,
    ATTR_BATTERY_LOW_THRESHOLD,
    EVENT_BATTERY_NOT_REPORTED,
    ATTR_PREVIOUS_BATTERY_LEVEL,
    ATTR_BATTERY_TYPE_AND_QUANTITY,
    ATTR_BATTERY_LAST_REPORTED_DAYS,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    SERVICE_BATTERY_REPLACED_SCHEMA,
    SERVICE_DATA_DATE_TIME_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPORTED,
    ATTR_BATTERY_LAST_REPORTED_LEVEL,
    SERVICE_CHECK_BATTERY_LAST_REPORTED,
    SERVICE_CHECK_BATTERY_LAST_REPORTED_SCHEMA,
)
from .common import utcnow_no_timezone
from .coordinator import BatteryNotesConfigEntry

_LOGGER = logging.getLogger(__name__)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the Mastodon integration."""

    hass.services.async_register(
        DOMAIN,
        SERVICE_BATTERY_REPLACED,
        _async_battery_replaced,
        schema=SERVICE_BATTERY_REPLACED_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LAST_REPORTED,
        _async_battery_last_reported,
        schema=SERVICE_CHECK_BATTERY_LAST_REPORTED_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LOW,
        _async_battery_low,
    )


async def _async_battery_replaced(call: ServiceCall) -> ServiceResponse:  # noqa: PLR0912
    """Handle the service call."""
    device_id = call.data.get(ATTR_DEVICE_ID, "")
    source_entity_id = call.data.get(ATTR_SOURCE_ENTITY_ID, "")
    datetime_replaced_entry = call.data.get(SERVICE_DATA_DATE_TIME_REPLACED)

    if datetime_replaced_entry:
        datetime_replaced = dt_util.as_utc(datetime_replaced_entry).replace(tzinfo=None)
    else:
        datetime_replaced = utcnow_no_timezone()

    entity_registry = er.async_get(call.hass)
    device_registry = dr.async_get(call.hass)

    if source_entity_id:
        source_entity_entry = entity_registry.async_get(source_entity_id)
        if not source_entity_entry:
            _LOGGER.error(
                "Entity %s not found",
                source_entity_id,
            )
            return None

        # Check if entity_id exists in any sub config entry
        entity_found = False

        for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
            battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
            if not battery_notes_config_entry.runtime_data.subentry_coordinators:
                continue

            for (
                coordinator
            ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
                if (
                    coordinator.source_entity_id
                    and coordinator.source_entity_id == source_entity_id
                ):
                    entity_found = True
                    coordinator.last_replaced = datetime_replaced
                    await coordinator.async_request_refresh()

                    _LOGGER.debug(
                        "Entity %s battery replaced on %s",
                        source_entity_id,
                        str(datetime_replaced),
                    )

                    call.hass.bus.async_fire(
                        EVENT_BATTERY_REPLACED,
                        {
                            ATTR_DEVICE_ID: coordinator.device_id or "",
                            ATTR_SOURCE_ENTITY_ID: coordinator.source_entity_id or "",
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

        if not entity_found:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_configured_in_battery_notes",
                translation_placeholders={"source": source_entity_id},
            )
        return None

    else:
        device_entry = device_registry.async_get(device_id)
        if not device_entry:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_configured_in_battery_notes",
                translation_placeholders={"source": device_id},
            )

        # Check if device_id exists in any sub config entry
        device_found = False
        for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
            battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
            if not battery_notes_config_entry.runtime_data.subentry_coordinators:
                continue

            for (
                coordinator
            ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
                if coordinator.device_id == device_id:
                    device_found = True
                    coordinator.last_replaced = datetime_replaced
                    await coordinator.async_request_refresh()

                    _LOGGER.debug(
                        "Device %s battery replaced on %s",
                        device_id,
                        str(datetime_replaced),
                    )

                    call.hass.bus.async_fire(
                        EVENT_BATTERY_REPLACED,
                        {
                            ATTR_DEVICE_ID: coordinator.device_id or "",
                            ATTR_SOURCE_ENTITY_ID: coordinator.source_entity_id or "",
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

            if not device_found:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="not_configured_in_battery_notes",
                    translation_placeholders={"source": device_id},
                )
        return None


async def _async_battery_last_reported(call: ServiceCall) -> ServiceResponse:
    """Handle the service call."""
    days_last_reported = cast(int, call.data.get(SERVICE_DATA_DAYS_LAST_REPORTED))

    for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
        battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
        if not battery_notes_config_entry.runtime_data.subentry_coordinators:
            continue

        for (
            coordinator
        ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
            if coordinator.wrapped_battery and coordinator.last_reported:
                time_since_lastreported = (
                    datetime.fromisoformat(str(utcnow_no_timezone()) + "+00:00")
                    - coordinator.last_reported
                )

                if time_since_lastreported.days > days_last_reported:
                    call.hass.bus.async_fire(
                        EVENT_BATTERY_NOT_REPORTED,
                        {
                            ATTR_DEVICE_ID: coordinator.device_id or "",
                            ATTR_SOURCE_ENTITY_ID: coordinator.source_entity_id or "",
                            ATTR_DEVICE_NAME: coordinator.device_name,
                            ATTR_BATTERY_TYPE_AND_QUANTITY: coordinator.battery_type_and_quantity,
                            ATTR_BATTERY_TYPE: coordinator.battery_type,
                            ATTR_BATTERY_QUANTITY: coordinator.battery_quantity,
                            ATTR_BATTERY_LAST_REPORTED: coordinator.last_reported,
                            ATTR_BATTERY_LAST_REPORTED_DAYS: time_since_lastreported.days,
                            ATTR_BATTERY_LAST_REPORTED_LEVEL: coordinator.last_reported_level,
                            ATTR_BATTERY_LAST_REPLACED: coordinator.last_replaced,
                        },
                    )

                    _LOGGER.debug(
                        "Raised event device %s not reported since %s",
                        coordinator.device_id,
                        str(coordinator.last_reported),
                    )
    return None


async def _async_battery_low(call: ServiceCall) -> ServiceResponse:
    """Handle the service call."""

    for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
        battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
        if not battery_notes_config_entry.runtime_data.subentry_coordinators:
            continue

        for (
            coordinator
        ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
            if coordinator.battery_low is True:
                call.hass.bus.async_fire(
                    EVENT_BATTERY_THRESHOLD,
                    {
                        ATTR_DEVICE_ID: coordinator.device_id or "",
                        ATTR_DEVICE_NAME: coordinator.device_name,
                        ATTR_SOURCE_ENTITY_ID: coordinator.source_entity_id or "",
                        ATTR_BATTERY_LOW: coordinator.battery_low,
                        ATTR_BATTERY_LOW_THRESHOLD: coordinator.battery_low_threshold,
                        ATTR_BATTERY_TYPE_AND_QUANTITY: coordinator.battery_type_and_quantity,
                        ATTR_BATTERY_TYPE: coordinator.battery_type,
                        ATTR_BATTERY_QUANTITY: coordinator.battery_quantity,
                        ATTR_BATTERY_LEVEL: coordinator.rounded_battery_level,
                        ATTR_PREVIOUS_BATTERY_LEVEL: coordinator.rounded_previous_battery_level,
                        ATTR_BATTERY_LAST_REPLACED: coordinator.last_replaced,
                        ATTR_BATTERY_THRESHOLD_REMINDER: True,
                    },
                )

                _LOGGER.debug(
                    "Raised event device %s battery low",
                    coordinator.device_id,
                )
    return None

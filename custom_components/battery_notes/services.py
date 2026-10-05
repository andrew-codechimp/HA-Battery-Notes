"""Define services for the Battery Notes integration."""

import logging
from datetime import datetime
from typing import Any, cast

from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_BATTERY_LAST_REPLACED,
    ATTR_BATTERY_LAST_REPLACED_DAYS,
    ATTR_BATTERY_LAST_REPORTED,
    ATTR_BATTERY_LAST_REPORTED_DAYS,
    ATTR_BATTERY_LAST_REPORTED_LEVEL,
    ATTR_DEVICE_ID,
    ATTR_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_NOT_REPLACED,
    EVENT_BATTERY_NOT_REPORTED,
    EVENT_BATTERY_REPLACED,
    EVENT_BATTERY_THRESHOLD,
    SERVICE_BATTERY_REPLACED,
    SERVICE_BATTERY_REPLACED_SCHEMA,
    SERVICE_CHECK_BATTERY_LAST_REPLACED,
    SERVICE_CHECK_BATTERY_LAST_REPLACED_SCHEMA,
    SERVICE_CHECK_BATTERY_LAST_REPORTED,
    SERVICE_CHECK_BATTERY_LAST_REPORTED_SCHEMA,
    SERVICE_CHECK_BATTERY_LOW,
    SERVICE_CHECK_BATTERY_LOW_SCHEMA,
    SERVICE_DATA_DATE_TIME_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPLACED,
    SERVICE_DATA_DAYS_LAST_REPORTED,
    SERVICE_DATA_RAISE_EVENTS,
)
from .coordinator import BatteryNotesConfigEntry

_LOGGER = logging.getLogger(__name__)


def _response_item(data: dict[str, Any]) -> dict[str, Any]:
    """Return event data as a service response item, datetimes as ISO strings."""
    return {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in data.items()
    }


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Set up the services for the Battery Notes integration."""

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
        supports_response=SupportsResponse.OPTIONAL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LAST_REPLACED,
        _async_battery_last_replaced,
        schema=SERVICE_CHECK_BATTERY_LAST_REPLACED_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHECK_BATTERY_LOW,
        _async_battery_low,
        schema=SERVICE_CHECK_BATTERY_LOW_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def _async_battery_replaced(call: ServiceCall) -> ServiceResponse:  # noqa: PLR0912
    """Handle the service call."""
    device_id = call.data.get(ATTR_DEVICE_ID, "")
    source_entity_id = call.data.get(ATTR_SOURCE_ENTITY_ID, "")
    datetime_replaced_entry = call.data.get(SERVICE_DATA_DATE_TIME_REPLACED)

    if datetime_replaced_entry:
        datetime_replaced = dt_util.as_utc(datetime_replaced_entry).replace(
            microsecond=1
        )
    else:
        datetime_replaced = dt_util.utcnow()

    entity_registry = er.async_get(call.hass)
    device_registry = dr.async_get(call.hass)

    if source_entity_id:
        source_entity_entry = entity_registry.async_get(source_entity_id)
        if not source_entity_entry:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_configured_in_battery_notes",
                translation_placeholders={"source": source_entity_id},
            )

        # Check if entity_id exists in any sub config entry
        for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
            battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
            if not battery_notes_config_entry.runtime_data.subentry_coordinators:
                continue

            for (
                coordinator
            ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
                if (
                    not coordinator.is_orphaned
                    and coordinator.source_entity_id
                    and coordinator.source_entity_id == source_entity_id
                ):
                    coordinator.last_replaced = datetime_replaced
                    await coordinator.async_request_refresh()

                    _LOGGER.debug(
                        "Entity %s battery replaced on %s",
                        source_entity_id,
                        str(datetime_replaced),
                    )

                    call.hass.bus.async_fire(
                        EVENT_BATTERY_REPLACED, coordinator.event_data()
                    )

                    _LOGGER.debug(
                        "Raised event battery replaced %s",
                        coordinator.device_id,
                    )

                    return None

        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="not_configured_in_battery_notes",
            translation_placeholders={"source": source_entity_id},
        )

    device_entry = device_registry.async_get(device_id)
    if not device_entry:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="not_configured_in_battery_notes",
            translation_placeholders={"source": device_id},
        )

    # Check if device_id exists in any sub config entry
    for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
        battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
        if not battery_notes_config_entry.runtime_data.subentry_coordinators:
            continue

        for (
            coordinator
        ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
            if not coordinator.is_orphaned and coordinator.device_id == device_id:
                coordinator.last_replaced = datetime_replaced
                await coordinator.async_request_refresh()

                _LOGGER.debug(
                    "Device %s battery replaced on %s",
                    device_id,
                    str(datetime_replaced),
                )

                call.hass.bus.async_fire(
                    EVENT_BATTERY_REPLACED, coordinator.event_data()
                )

                _LOGGER.debug(
                    "Raised event battery replaced %s",
                    coordinator.device_id,
                )

                # Found and dealt with, exit
                return None

    raise HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="not_configured_in_battery_notes",
        translation_placeholders={"source": device_id},
    )


async def _async_battery_last_replaced(call: ServiceCall) -> ServiceResponse:
    """Handle the service call."""
    days_last_replaced = cast(int, call.data.get(SERVICE_DATA_DAYS_LAST_REPLACED))
    raise_events = call.data.get(SERVICE_DATA_RAISE_EVENTS, True)

    entity_registry = er.async_get(call.hass)

    return_items: list[dict[str, Any]] = []

    for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
        battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
        if not battery_notes_config_entry.runtime_data.subentry_coordinators:
            continue

        for (
            coordinator
        ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
            if not coordinator.is_orphaned and coordinator.last_replaced:
                # Skip if last replaced sensor is disabled
                last_replaced_entity_id = entity_registry.async_get_entity_id(
                    "sensor",
                    DOMAIN,
                    f"{coordinator.subentry.unique_id}_battery_last_replaced",
                )

                if last_replaced_entity_id:
                    last_replaced_entity_entry = entity_registry.async_get(
                        last_replaced_entity_id
                    )
                    if (
                        last_replaced_entity_entry
                        and last_replaced_entity_entry.disabled
                    ):
                        continue

                time_since_last_replaced = dt_util.utcnow() - coordinator.last_replaced

                if time_since_last_replaced.days > days_last_replaced:
                    data = coordinator.event_data(
                        {
                            ATTR_BATTERY_LAST_REPORTED: coordinator.last_reported,
                            ATTR_BATTERY_LAST_REPORTED_LEVEL: coordinator.last_reported_level,
                            ATTR_BATTERY_LAST_REPLACED: coordinator.last_replaced,
                            ATTR_BATTERY_LAST_REPLACED_DAYS: time_since_last_replaced.days,
                        }
                    )
                    if raise_events:
                        call.hass.bus.async_fire(EVENT_BATTERY_NOT_REPLACED, data)
                        _LOGGER.debug(
                            "Raised event device %s battery not replaced since %s",
                            coordinator.device_id,
                            str(coordinator.last_replaced),
                        )

                    return_items.append(_response_item(data))

    if call.return_response:
        return {"check_battery_last_replaced": cast(Any, return_items)}
    return None


async def _async_battery_last_reported(call: ServiceCall) -> ServiceResponse:
    """Handle the service call."""
    days_last_reported = cast(int, call.data.get(SERVICE_DATA_DAYS_LAST_REPORTED))
    raise_events = call.data.get(SERVICE_DATA_RAISE_EVENTS, True)

    return_items: list[dict[str, Any]] = []

    for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
        battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
        if not battery_notes_config_entry.runtime_data.subentry_coordinators:
            continue

        for (
            coordinator
        ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
            if not coordinator.is_orphaned and (
                coordinator.wrapped_battery or coordinator.wrapped_battery_low
            ):
                time_since_last_reported = None
                if coordinator.last_reported:
                    time_since_last_reported = (
                        dt_util.utcnow() - coordinator.last_reported
                    )
                last_reported_days = (
                    time_since_last_reported.days
                    if time_since_last_reported is not None
                    else None
                )
                if (
                    time_since_last_reported is None
                    or time_since_last_reported.days > days_last_reported
                ):
                    data = coordinator.event_data(
                        {
                            ATTR_BATTERY_LAST_REPORTED: coordinator.last_reported,
                            ATTR_BATTERY_LAST_REPORTED_DAYS: last_reported_days,
                            ATTR_BATTERY_LAST_REPORTED_LEVEL: coordinator.last_reported_level,
                            ATTR_BATTERY_LAST_REPLACED: coordinator.last_replaced,
                        }
                    )
                    if raise_events:
                        call.hass.bus.async_fire(EVENT_BATTERY_NOT_REPORTED, data)
                        _LOGGER.debug(
                            "Raised event device %s not reported since %s",
                            coordinator.device_id,
                            str(coordinator.last_reported),
                        )

                    return_items.append(_response_item(data))

    if call.return_response:
        return {"check_battery_last_reported": cast(Any, return_items)}
    return None


async def _async_battery_low(call: ServiceCall) -> ServiceResponse:
    """Handle the service call."""
    raise_events = call.data.get(SERVICE_DATA_RAISE_EVENTS, True)

    return_items: list[dict[str, Any]] = []

    for config_entry in call.hass.config_entries.async_loaded_entries(DOMAIN):
        battery_notes_config_entry = cast(BatteryNotesConfigEntry, config_entry)
        if not battery_notes_config_entry.runtime_data.subentry_coordinators:
            continue

        for (
            coordinator
        ) in battery_notes_config_entry.runtime_data.subentry_coordinators.values():
            if not coordinator.is_orphaned and coordinator.battery_low is True:
                data = coordinator.battery_level_event_data(
                    coordinator.rounded_battery_level,
                    coordinator.rounded_previous_battery_level,
                    reminder=True,
                )
                if raise_events:
                    call.hass.bus.async_fire(EVENT_BATTERY_THRESHOLD, data)
                    _LOGGER.debug(
                        "Raised event device %s battery low",
                        coordinator.device_id,
                    )
                return_items.append(_response_item(data))

    if call.return_response:
        return {"check_battery_battery_low": cast(Any, return_items)}
    return None

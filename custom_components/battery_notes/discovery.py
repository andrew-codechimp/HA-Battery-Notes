from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.device_registry as dr
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_BATTERY_TYPE,
    DOMAIN,
)
from .library import ModelInfo, DeviceBatteryDetails, Library

_LOGGER = logging.getLogger(__name__)


async def autodiscover_model(
    device_entry: dr.DeviceEntry | None,
) -> ModelInfo | None:
    """Try to auto discover manufacturer and model from the known device information."""
    if not device_entry:
        return None

    model_info = await get_model_information(device_entry)
    if not model_info:
        _LOGGER.debug(
            "%s: Cannot autodiscover model, manufacturer or model unknown from device registry",
            device_entry.id,
        )
        return None

    _LOGGER.debug(
        "%s: Auto discovered model (manufacturer=%s, model=%s)",
        device_entry.id,
        model_info.manufacturer,
        model_info.model,
    )
    return model_info


async def get_model_information(
    device_entry: dr.DeviceEntry,
) -> DeviceBatteryDetails | None:
    """See if we have enough information in device registry to automatically setup the battery type."""

    manufacturer = str(device_entry.manufacturer)
    model = str(device_entry.model)

    if len(manufacturer) == 0 or len(model) == 0:
        return None

    return ModelInfo(manufacturer, model)


class DiscoveryManager:
    """This class is responsible for scanning the HA instance for devices and their manufacturer / model info
    It checks if any of these devices is supported in the batterynotes library
    When devices are found it will dispatch a discovery flow, so the user can add them to their HA instance.
    """

    def __init__(self, hass: HomeAssistant, ha_config: ConfigType) -> None:
        self.hass = hass
        self.ha_config = ha_config
        self.manually_configured_entities: list[str] | None = None

    async def start_discovery(self) -> None:
        """Start the discovery procedure."""
        _LOGGER.debug("Start auto discovering devices")
        device_registry = dr.async_get(self.hass)

        library = Library()

        for device_entry in list(device_registry.devices.values()):
            if not self.should_process_device(device_entry):
                continue

            model_info = await autodiscover_model(device_entry)
            if not model_info or not model_info.manufacturer or not model_info.model:
                continue

            device_battery_details = await library.get_device_battery_details(
                model_info.manufacturer, model_info.model
            )

            if not device_battery_details:
                continue

            self._init_entity_discovery(device_entry.id, device_battery_details)

        _LOGGER.debug("Done auto discovering entities")

    def should_process_device(self, device_entry: dr.DeviceEntry) -> bool:
        """Do some validations on the registry entry to see if it qualifies for discovery."""
        if device_entry.disabled:
            return False

        return True

    @callback
    def _init_entity_discovery(
        self,
        device_id: str,
        device_battery_details: DeviceBatteryDetails | None,
    ) -> None:
        """Dispatch the discovery flow for a given entity."""
        existing_entries = [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.unique_id == f"bn_{device_id}"
        ]
        if existing_entries:
            _LOGGER.debug(
                "%s: Already setup with discovery, skipping new discovery",
                f"bn_{device_id}",
            )
            return

        discovery_data: dict[str, Any] = {
            CONF_DEVICE_ID: device_id,
        }

        if device_battery_details:
            discovery_data[
                CONF_BATTERY_TYPE
            ] = device_battery_details.battery_type_and_quantity

        discovery_flow.async_create_flow(
            self.hass,
            DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data=discovery_data,
        )

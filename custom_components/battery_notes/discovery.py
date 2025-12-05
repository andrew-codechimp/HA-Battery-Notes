"""Discovery of devices with a battery definition."""

from __future__ import annotations

import logging
from typing import Any

import homeassistant.helpers.device_registry as dr
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.loader import Integration, async_get_integration
from homeassistant.helpers import discovery_flow
from homeassistant.config_entries import SOURCE_IGNORE, SOURCE_INTEGRATION_DISCOVERY

from .const import (
    DOMAIN,
    CONF_MODEL,
    CONF_MODEL_ID,
    CONF_HW_VERSION,
    CONF_DEVICE_NAME,
    CONF_BATTERY_TYPE,
    CONF_MANUFACTURER,
    CONF_BATTERY_QUANTITY,
    CONF_INTEGRATION_NAME,
)
from .common import get_device_model_id
from .library import DATA_LIBRARY, ModelInfo, DeviceBatteryDetails
from .coordinator import BatteryNotesDomainConfig

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
            "%s: Cannot autodiscover device, manufacturer or model unknown from device registry",
            device_entry.id,
        )
        return None

    _LOGGER.debug(
        "%s: Auto discovered device (manufacturer=%s, model=%s)",
        device_entry.id,
        model_info.manufacturer,
        model_info.model,
    )
    return model_info


async def get_model_information(
    device_entry: dr.DeviceEntry,
) -> ModelInfo | None:
    """See if we have enough information to automatically setup the battery type."""

    manufacturer = device_entry.manufacturer
    model = device_entry.model
    model_id = get_device_model_id(device_entry)
    hw_version = device_entry.hw_version

    if not manufacturer or not model:
        return None

    return ModelInfo(manufacturer, model, model_id, hw_version)


class DiscoveryManager:
    """Device Discovery.

    This class is responsible for scanning the HA instance for devices and their
    manufacturer / model info
    It checks if any of these devices is supported in the batterynotes library
    When devices are found it will dispatch a discovery flow,
    so the user can add them to their HA instance.
    """

    def __init__(
        self, hass: HomeAssistant, ha_config: BatteryNotesDomainConfig
    ) -> None:
        """Init."""
        self.hass = hass
        self.ha_config = ha_config

    async def start_discovery(self) -> None:
        """Start the discovery procedure."""
        _LOGGER.debug("Start auto discovering devices")
        device_registry = dr.async_get(self.hass)

        library = self.hass.data[DATA_LIBRARY]
        if not library.is_loaded:
            await library.load_libraries()

        if library.is_loaded:
            for device_entry in list(device_registry.devices.values()):
                if not self.should_process_device(device_entry):
                    continue

                model_info = await autodiscover_model(device_entry)
                if (
                    not model_info
                    or not model_info.manufacturer
                    or not model_info.model
                ):
                    continue

                device_battery_details = await library.get_device_battery_details(
                    model_info
                )

                if not device_battery_details:
                    continue

                if device_battery_details.is_manual:
                    continue

                config_entry_id = next(iter(device_entry.config_entries))
                config_entry = self.hass.config_entries.async_get_entry(config_entry_id)
                if config_entry:
                    integration = await async_get_integration(
                        self.hass, config_entry.domain
                    )

                self._init_entity_discovery(
                    device_entry, device_battery_details, integration or None
                )
        else:
            _LOGGER.error("Library not loaded")

        _LOGGER.debug("Done auto discovering devices")

    def should_process_device(self, device_entry: dr.DeviceEntry) -> bool:
        """Do some validations on the registry entry to see if it qualifies for discovery."""
        return not device_entry.disabled

    @callback
    def _init_entity_discovery(
        self,
        device_entry: dr.DeviceEntry,
        device_battery_details: DeviceBatteryDetails,
        integration: Integration | None,
    ) -> None:
        """Dispatch the discovery flow for a given entity."""
        unique_id = f"bn_{device_entry.id}"

        # Iterate all the ignored devices and check if we have it already
        for config_entry in self.hass.config_entries.async_entries(
            domain=DOMAIN, include_ignore=True, include_disabled=False
        ):
            if (
                config_entry.source == SOURCE_IGNORE
                and config_entry.unique_id == unique_id
            ):
                _LOGGER.debug(
                    "%s: Ignored, skipping new discovery",
                    unique_id,
                )
                return

        for config_entry in self.hass.config_entries.async_entries(
            domain=DOMAIN, include_ignore=False, include_disabled=False
        ):
            for subentry in config_entry.subentries.values():
                if subentry.data.get(CONF_DEVICE_ID, "") == device_entry.id:
                    _LOGGER.debug(
                        "%s: Already setup, skipping new discovery",
                        unique_id,
                    )
                    return

        discovery_data: dict[str, Any] = {
            CONF_DEVICE_ID: device_entry.id,
        }

        if device_battery_details:
            discovery_data[CONF_BATTERY_TYPE] = device_battery_details.battery_type
            discovery_data[CONF_BATTERY_QUANTITY] = (
                device_battery_details.battery_quantity
            )
        discovery_data[CONF_MANUFACTURER] = device_battery_details.manufacturer
        discovery_data[CONF_MODEL] = device_battery_details.model
        discovery_data[CONF_MODEL_ID] = get_device_model_id(device_entry)
        discovery_data[CONF_HW_VERSION] = device_battery_details.hw_version
        discovery_data[CONF_DEVICE_NAME] = get_wrapped_device_name(
            device_entry.id, device_entry
        )
        discovery_data[CONF_INTEGRATION_NAME] = (
            integration.name if integration else None
        )

        discovery_flow.async_create_flow(
            self.hass,
            DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data=discovery_data,
        )


def get_wrapped_device_name(
    device_id: str,
    device_entry: dr.DeviceEntry | None,
) -> str:
    """Construct device name based on the wrapped device."""
    if device_entry:
        return device_entry.name_by_user or device_entry.name or device_id

    return device_id

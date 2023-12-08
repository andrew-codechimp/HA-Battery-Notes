from __future__ import annotations

import logging
import re
from typing import Any

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import SOURCE_INTEGRATION_DISCOVERY, SOURCE_USER
from homeassistant.const import CONF_ENTITY_ID, CONF_PLATFORM
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import discovery_flow
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.typing import ConfigType

from .common import SourceEntity, create_source_entity
from .const import (
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_SENSORS,
    DOMAIN,
)
from .library import ModelInfo, DeviceBatteryDetails, get_device_battery_details
from .errors import ModelNotSupportedError

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
        for device_entry in list(device_registry.devices.values()):
            if not self.should_process_device(device_entry):
                continue

            if not self.should_process_entity(entity_entry):
                continue

            model_info = await autodiscover_model(device_entry)
            if not model_info or not model_info.manufacturer or not model_info.model:
                continue

            source_entity = await create_source_entity(
                entity_entry.entity_id,
                self.hass,
            )

            device_battery_details = get_device_battery_details(
                model_info.manufacturer, model_info.model
            )

            if not device_battery_details:
                continue

            self._init_entity_discovery(source_entity, device_battery_details, {})

        _LOGGER.debug("Done auto discovering entities")

    def should_process_device(self, device_entry: dr.DeviceEntry) -> bool:
        """Do some validations on the registry entry to see if it qualifies for discovery."""
        if device_entry.disabled:
            return False

        has_user_config = self._is_user_configured(entity_entry.entity_id)
        if has_user_config:
            _LOGGER.debug(
                "%s: Device is already configured, skipping auto configuration",
                device_entry.id,
            )
            return False

        return True

    def should_process_entity(self, entity_entry: er.RegistryEntry) -> bool:
        """Do some validations on the registry entry to see if it qualifies for discovery."""
        if entity_entry.disabled:
            return False

        if entity_entry.domain not in DEVICE_DOMAINS.values():
            return False

        if entity_entry.entity_category in [
            EntityCategory.CONFIG,
            EntityCategory.DIAGNOSTIC,
        ]:
            return False

        has_user_config = self._is_user_configured(entity_entry.entity_id)
        if has_user_config:
            _LOGGER.debug(
                "%s: Entity is manually configured, skipping auto configuration",
                entity_entry.entity_id,
            )
            return False

        return True

    @callback
    def _init_entity_discovery(
        self,
        source_entity: SourceEntity,
        power_profile: PowerProfile | None,
        extra_discovery_data: dict | None,
    ) -> None:
        """Dispatch the discovery flow for a given entity."""
        existing_entries = [
            entry
            for entry in self.hass.config_entries.async_entries(DOMAIN)
            if entry.unique_id
            in [source_entity.unique_id, f"pc_{source_entity.unique_id}"]
        ]
        if existing_entries:
            _LOGGER.debug(
                f"{source_entity.entity_id}: Already setup with discovery, skipping new discovery",
            )
            return

        discovery_data: dict[str, Any] = {
            CONF_ENTITY_ID: source_entity.entity_id,
            DISCOVERY_SOURCE_ENTITY: source_entity,
        }

        if power_profile:
            discovery_data[DISCOVERY_POWER_PROFILE] = power_profile
            discovery_data[CONF_MANUFACTURER] = power_profile.manufacturer
            discovery_data[CONF_MODEL] = power_profile.model

        if extra_discovery_data:
            discovery_data.update(extra_discovery_data)

        discovery_flow.async_create_flow(
            self.hass,
            DOMAIN,
            context={"source": SOURCE_INTEGRATION_DISCOVERY},
            data=discovery_data,
        )

    def _is_user_configured(self, entity_id: str) -> bool:
        """Check if user have setup powercalc sensors for a given entity_id.
        Either with the YAML or GUI method.
        """
        if not self.manually_configured_entities:
            self.manually_configured_entities = (
                self._load_manually_configured_entities()
            )

        return entity_id in self.manually_configured_entities

    def _load_manually_configured_entities(self) -> list[str]:
        """Looks at the YAML and GUI config entries for all the configured entity_id's."""
        entities = []

        # Find entity ids in yaml config (Legacy)
        if SENSOR_DOMAIN in self.ha_config:  # pragma: no cover
            sensor_config = self.ha_config.get(SENSOR_DOMAIN)
            platform_entries = [
                item
                for item in sensor_config or {}
                if isinstance(item, dict) and item.get(CONF_PLATFORM) == DOMAIN
            ]
            for entry in platform_entries:
                entities.extend(self._find_entity_ids_in_yaml_config(entry))

        # Find entity ids in yaml config (New)
        domain_config: ConfigType = self.ha_config.get(DOMAIN, {})
        if CONF_SENSORS in domain_config:
            sensors = domain_config[CONF_SENSORS]
            for sensor_config in sensors:
                entities.extend(self._find_entity_ids_in_yaml_config(sensor_config))

        # Add entities from existing config entries
        entities.extend(
            [
                entry.data.get(CONF_ENTITY_ID)
                for entry in self.hass.config_entries.async_entries(DOMAIN)
                if entry.source == SOURCE_USER
            ],
        )

        return entities

    def _find_entity_ids_in_yaml_config(self, search_dict: dict) -> list[str]:
        """Takes a dict with nested lists and dicts,
        and searches all dicts for a key of the field
        provided.
        """
        found_entity_ids: list[str] = []

        for key, value in search_dict.items():
            if key == CONF_ENTITY_ID:
                found_entity_ids.append(value)

            elif isinstance(value, dict):
                results = self._find_entity_ids_in_yaml_config(value)
                for result in results:
                    found_entity_ids.append(result)  # pragma: no cover

            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        results = self._find_entity_ids_in_yaml_config(item)
                        for result in results:
                            found_entity_ids.append(result)

        return found_entity_ids

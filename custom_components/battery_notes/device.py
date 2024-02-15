"""Battery Notes device, contains device level details."""
import logging

from homeassistant.config_entries import ConfigEntry

from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.entity_registry import RegistryEntry

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.sensor import (
    SensorDeviceClass,
)

from homeassistant.const import (
    CONF_DEVICE_ID,
    PERCENTAGE,
)

from .const import (
    PLATFORMS,
    DOMAIN,
    DOMAIN_CONFIG,
    DATA,
    DATA_STORE,
    CONF_BATTERY_TYPE,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_LOW_TEMPLATE,
    DEFAULT_BATTERY_LOW_THRESHOLD,
)

from .store import BatteryNotesStorage
from .coordinator import BatteryNotesCoordinator

_LOGGER = logging.getLogger(__name__)


class BatteryNotesDevice:
    """Manages a Battery Note device."""

    config: ConfigEntry = None
    store: BatteryNotesStorage = None
    coordinator: BatteryNotesCoordinator = None
    wrapped_battery: RegistryEntry = None
    device_name: str = None

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the device."""
        self.hass = hass
        self.config = config
        self.reset_jobs: list[CALLBACK_TYPE] = []

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self.device_name or self.config.title

    @property
    def unique_id(self) -> str | None:
        """Return the unique id of the device."""
        return self.config.unique_id

    @staticmethod
    async def async_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Update the device and related entities.

        Triggered when the device is renamed on the frontend.
        """
        await hass.config_entries.async_reload(entry.entry_id)

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        config = self.config

        device_id = config.data.get(CONF_DEVICE_ID)

        # Find a battery for this device
        entity_registry = er.async_get(self.hass)
        device_registry = dr.async_get(self.hass)
        for entity in entity_registry.entities.values():
            if not entity.device_id or entity.device_id != device_id:
                continue
            if not entity.domain or entity.domain != SENSOR_DOMAIN:
                continue
            if not entity.platform or entity.platform == DOMAIN:
                continue

            if entity.disabled:
                continue

            device_class = entity.device_class or entity.original_device_class
            if device_class != SensorDeviceClass.BATTERY:
                continue

            if entity.unit_of_measurement != PERCENTAGE:
                continue

            self.wrapped_battery = entity_registry.async_get(entity.entity_id)

        device_entry = device_registry.async_get(device_id)
        if device_entry:
            self.device_name = (
                device_entry.name_by_user or device_entry.name or self.config.title
            )
        else:
            self.device_name = self.config.title

        self.store = self.hass.data[DOMAIN][DATA_STORE]
        self.coordinator = BatteryNotesCoordinator(
            self.hass, self.store, self.wrapped_battery
        )

        self.coordinator.device_id = device_id
        self.coordinator.device_name = self.device_name
        self.coordinator.battery_type = config.data.get(CONF_BATTERY_TYPE)
        try:
            self.coordinator.battery_quantity = int(
                config.data.get(CONF_BATTERY_QUANTITY)
            )
        except ValueError:
            self.coordinator.battery_quantity = 1

        self.coordinator.battery_low_threshold = int(
            config.data.get(CONF_BATTERY_LOW_THRESHOLD, 0)
        )

        if self.coordinator.battery_low_threshold == 0:
            domain_config: dict = self.hass.data[DOMAIN][DOMAIN_CONFIG]
            self.coordinator.battery_low_threshold = domain_config.get(
                CONF_DEFAULT_BATTERY_LOW_THRESHOLD, DEFAULT_BATTERY_LOW_THRESHOLD
            )

        self.coordinator.battery_low_template = config.data.get(CONF_BATTERY_LOW_TEMPLATE)

        if self.wrapped_battery:
            _LOGGER.debug(
                "%s low threshold set at %d",
                self.wrapped_battery.entity_id,
                self.coordinator.battery_low_threshold,
            )

        self.hass.data[DOMAIN][DATA].devices[config.entry_id] = self
        self.reset_jobs.append(config.add_update_listener(self.async_update))

        # Forward entry setup to related domains.
        await self.hass.config_entries.async_forward_entry_setups(config, PLATFORMS)

        return True

    async def async_unload(self) -> bool:
        """Unload the device and related entities."""

        while self.reset_jobs:
            self.reset_jobs.pop()()

        return True

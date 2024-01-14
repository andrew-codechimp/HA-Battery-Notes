"""Battery Notes device, contains device level details."""
from contextlib import suppress
from functools import partial
import logging


from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.const import (
    CONF_NAME,
    Platform,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (
    PLATFORMS,
    DOMAIN,
    DATA,
    DATA_STORE,
)

from .store import BatteryNotesStorage
from .coordinator import BatteryNotesCoordinator

_LOGGER = logging.getLogger(__name__)


class BatteryNotesDevice:
    """Manages a Battery Note device."""

    store: BatteryNotesStorage = None
    coordinator: BatteryNotesCoordinator = None

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the device."""
        self.hass = hass
        self.config = config
        self.reset_jobs: list[CALLBACK_TYPE] = []

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self.config.title

    @property
    def unique_id(self) -> str | None:
        """Return the unique id of the device."""
        return self.config.unique_id

    @staticmethod
    async def async_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Update the device and related entities.

        Triggered when the device is renamed on the frontend.
        """
        device_registry = dr.async_get(hass)
        assert entry.unique_id
        device_entry = device_registry.async_get_device(
            identifiers={(DOMAIN, entry.unique_id)}
        )
        assert device_entry
        device_registry.async_update_device(device_entry.id, name=entry.title)
        await hass.config_entries.async_reload(entry.entry_id)

    async def async_setup(self) -> bool:
        """Set up the device and related entities."""
        config = self.config

        self.store = self.hass.data[DOMAIN][DATA_STORE]
        self.coordinator = BatteryNotesCoordinator(self.hass, self.store)

        self.hass.data[DOMAIN][DATA].devices[config.entry_id] = self
        self.reset_jobs.append(config.add_update_listener(self.async_update))

        # Forward entry setup to related domains.
        await self.hass.config_entries.async_forward_entry_setups(
            config, PLATFORMS
        )

        return True

    async def async_unload(self) -> bool:
        """Unload the device and related entities."""
        if self.update_manager is None:
            return True

        while self.reset_jobs:
            self.reset_jobs.pop()()

        return await self.hass.config_entries.async_unload_platforms(
            self.config, PLATFORMS
        )

"""Battery Notes device, contains device level details."""
from contextlib import suppress
from functools import partial
import logging


from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_TIMEOUT,
    CONF_TYPE,
    Platform,
)
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from .const import (
    DOMAIN,
    DATA_DEVICES,
    DATA_STORE,
)

from .store import BatteryNotesStorage
from .coordinator import BatteryNotesCoordinator

_LOGGER = logging.getLogger(__name__)


def get_domains(device_type: str) -> set[Platform]:
    """Return the domains available for a device type."""
    return {d for d, t in DOMAINS_AND_TYPES.items() if device_type in t}


class BatteryNotesDevice:
    """Manages a Battery Note device."""

    store: BatteryNotesStorage = None
    coordinator: BatteryNotesCoordinator = None

    def __init__(self, hass: HomeAssistant, config: ConfigEntry) -> None:
        """Initialize the device."""
        self.hass = hass
        self.config = config

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

        self.hass.data[DOMAIN][DATA_DEVICES].devices[config.entry_id] = self
        self.reset_jobs.append(config.add_update_listener(self.async_update))

        # Forward entry setup to related domains.
        await self.hass.config_entries.async_forward_entry_setups(
            config, get_domains(self.api.type)
        )

        return True

    async def async_unload(self) -> bool:
        """Unload the device and related entities."""
        if self.update_manager is None:
            return True

        while self.reset_jobs:
            self.reset_jobs.pop()()

        return await self.hass.config_entries.async_unload_platforms(
            self.config, get_domains(self.api.type)
        )

    async def async_auth(self) -> bool:
        """Authenticate to the device."""
        try:
            await self.hass.async_add_executor_job(self.api.auth)
        except (BroadlinkException, OSError) as err:
            _LOGGER.debug(
                "Failed to authenticate to the device at %s: %s", self.api.host[0], err
            )
            if isinstance(err, AuthenticationError):
                await self._async_handle_auth_error()
            return False
        return True

    async def async_request(self, function, *args, **kwargs):
        """Send a request to the device."""
        request = partial(function, *args, **kwargs)
        try:
            return await self.hass.async_add_executor_job(request)
        except (AuthorizationError, ConnectionClosedError):
            if not await self.async_auth():
                raise
            return await self.hass.async_add_executor_job(request)

    async def _async_handle_auth_error(self) -> None:
        """Handle an authentication error."""
        if self.authorized is False:
            return

        self.authorized = False

        _LOGGER.error(
            (
                "%s (%s at %s) is locked. Click Configuration in the sidebar, "
                "click Integrations, click Configure on the device and follow "
                "the instructions to unlock it"
            ),
            self.name,
            self.api.model,
            self.api.host[0],
        )

        self.hass.async_create_task(
            self.hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_REAUTH},
                data={CONF_NAME: self.name, **self.config.data},
            )
        )



"""DataUpdateCoordinator for battery notes."""
from __future__ import annotations

import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    ATTR_REMOVE,
)

_LOGGER = logging.getLogger(__name__)


class BatteryNotesCoordinator(DataUpdateCoordinator):
    """Define an object to hold Battery Notes device."""

    def __init__(self, hass, store):
        """Initialize."""
        self.hass = hass
        self.store = store

        super().__init__(hass, _LOGGER, name=DOMAIN)

    async def _async_update_data(self):
        """Update data."""

        _LOGGER.debug("Update coordinator")

    def async_update_device_config(self, device_id: str, data: dict):
        """Conditional create, update or remove device from store."""

        if ATTR_REMOVE in data:
            self.store.async_delete_device(device_id)
        elif self.store.async_get_device(device_id):
            self.store.async_update_device(device_id, data)
        else:
            self.store.async_create_device(device_id, data)

    async def async_delete_config(self):
        """Wipe battery notes storage."""

        await self.store.async_delete()

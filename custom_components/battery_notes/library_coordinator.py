"""DataUpdateCoordinator for battery notes library."""
from __future__ import annotations

from datetime import timedelta
import logging
import json
import os

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .library_updater import (
    LibraryUpdaterClient,
    LibraryUpdaterClientError,
)

from .const import DOMAIN, LOGGER

_LOGGER = logging.getLogger(__name__)

BUILT_IN_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "data")


class BatteryNotesLibraryUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching the library from GitHub."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: LibraryUpdaterClient,
    ) -> None:
        """Initialize."""
        self.client = client
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=1),
        )

    async def _async_update_data(self):
        """Update data via library."""
        try:
            _LOGGER.debug("Getting library updates")

            content = await self.client.async_get_data()

            if await self.validate_json(content):
                json_path = os.path.join(
                    BUILT_IN_DATA_DIRECTORY,
                    "library.json",
                )

                f = open(json_path, mode="w", encoding="utf-8")
                f.write(content)

                _LOGGER.debug("Updated library")
            else:
                _LOGGER.error("Library file is invalid, not updated")

        except LibraryUpdaterClientError as exception:
            raise UpdateFailed(exception) from exception

    async def validate_json(self, content: str) -> bool:
        """Check if content is valid json."""
        try:
            json.loads(content)
        except ValueError:
            return False
        return True

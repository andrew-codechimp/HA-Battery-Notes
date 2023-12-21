"""DataUpdateCoordinator for battery notes library."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
import json
import os

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .library_updater import (
    LibraryUpdaterClient,
    LibraryUpdaterClientError,
)

from .const import (
    DOMAIN,
    LOGGER,
    DATA_LIBRARY_LAST_UPDATE,
)

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
            update_interval=timedelta(hours=24),
        )

    async def _async_update_data(self):
        """Update data via library."""

        if await self.time_to_update_library() is False:
            return

        try:
            _LOGGER.debug("Getting library updates")

            content = await self.client.async_get_data()

            if validate_json(content):
                json_path = os.path.join(
                    BUILT_IN_DATA_DIRECTORY,
                    "library.json",
                )

                f = open(json_path, mode="w", encoding="utf-8")
                f.write(content)

                self.hass.data[DOMAIN][DATA_LIBRARY_LAST_UPDATE] = datetime.now()

                _LOGGER.debug("Updated library")
            else:
                _LOGGER.error("Library file is invalid, not updated")

        except LibraryUpdaterClientError as exception:
            raise UpdateFailed(exception) from exception

    async def time_to_update_library(self) -> bool:
        """Check when last updated and if OK to do a new library update."""
        try:
            if DATA_LIBRARY_LAST_UPDATE in self.hass.data[DOMAIN]:
                time_since_last_update = (
                    datetime.now() - self.hass.data[DOMAIN][DATA_LIBRARY_LAST_UPDATE]
                )

                time_difference_in_hours = time_since_last_update / timedelta(hours=1)

                if time_difference_in_hours < 23:
                    _LOGGER.debug("Skipping library updates")
                    return False
            return True
        except ConfigEntryNotReady:
            # Ignore as we are initial load
            return True


def validate_json(content: str) -> bool:
    """Check if content is valid json."""
    try:
        library = json.loads(content)

        if "version" not in library:
            return False

        if library["version"] > 1:
            return False
    except ValueError:
        return False
    return True

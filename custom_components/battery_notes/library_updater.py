"""Sample API Client."""
from __future__ import annotations

import logging
import asyncio
import socket
import json
import os
from datetime import datetime, timedelta

import aiohttp
import async_timeout

from homeassistant.exceptions import ConfigEntryNotReady

from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_utc_time_change

from .const import (
    CONF_LIBRARY_URL,
    DOMAIN,
    DATA_LIBRARY_LAST_UPDATE,
)

_LOGGER = logging.getLogger(__name__)

BUILT_IN_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "data")

class LibraryUpdaterClientError(Exception):
    """Exception to indicate a general API error."""


class LibraryUpdaterClientCommunicationError(LibraryUpdaterClientError):
    """Exception to indicate a communication error."""

class LibraryUpdater:
    """Library updater."""

    def __init__(self, hass):
        """Initialize the library updater."""
        self.hass = hass
        self._client = LibraryUpdaterClient(session=async_get_clientsession(hass))

        # Fire the library check every 24 hours from now
        async_track_utc_time_change(
            hass,
            self.timer_update,
            hour = datetime.now().hour,
            minute = 1,
            second=1)

    @callback
    async def timer_update(self, time):
        """Need to update the library."""
        if await self.time_to_update_library() is False:
            return

        await self.get_library_updates(time)

    @callback
    async def get_library_updates(self, time): # pylint: disable=unused-argument
        """Make a call to GitHub to get the latest library.json."""
        try:
            _LOGGER.debug("Getting library updates")

            content = await self._client.async_get_data()

            if self.validate_json(content):
                json_path = os.path.join(
                    BUILT_IN_DATA_DIRECTORY,
                    "library.json",
                )

                with open(json_path, "w", encoding="utf-8") as file:
                    file.write(content)
                    file.close()

                self.hass.data[DOMAIN][DATA_LIBRARY_LAST_UPDATE] = datetime.now()

                _LOGGER.debug("Updated library")
            else:
                _LOGGER.error("Library file is invalid, not updated")

        except LibraryUpdaterClientError:
            _LOGGER.error("Library update failed")

    async def time_to_update_library(self) -> bool:
        """Check when last updated and if OK to do a new library update."""
        try:
            if DATA_LIBRARY_LAST_UPDATE in self.hass.data[DOMAIN]:
                time_since_last_update = (
                    datetime.now() - self.hass.data[DOMAIN][DATA_LIBRARY_LAST_UPDATE]
                )

                time_difference_in_hours = time_since_last_update / timedelta(hours=1)

                if time_difference_in_hours < 23:
                    _LOGGER.debug("Skipping library update, too recent")
                    return False

            return True
        except ConfigEntryNotReady:
            # Ignore as we are initial load
            return True

    def validate_json(self, content: str) -> bool:
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

class LibraryUpdaterClient:
    """Library downloader."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Client to get latest library file from GitHub."""
        self._session = session

    async def async_get_data(self) -> any:
        """Get data from the API."""
        return await self._api_wrapper(method="get", url=CONF_LIBRARY_URL)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
    ) -> any:
        """Get information from the API."""
        try:
            async with async_timeout.timeout(10):
                response = await self._session.request(
                    method=method,
                    url=url,
                    allow_redirects=True,
                )
                # response.raise_for_status()
                return await response.text()

        except asyncio.TimeoutError as exception:
            raise LibraryUpdaterClientCommunicationError(
                "Timeout error fetching information",
            ) from exception
        except (aiohttp.ClientError, socket.gaierror) as exception:
            raise LibraryUpdaterClientCommunicationError(
                "Error fetching information",
            ) from exception
        except Exception as exception:  # pylint: disable=broad-except
            raise LibraryUpdaterClientError(
                "Something really wrong happened!"
            ) from exception

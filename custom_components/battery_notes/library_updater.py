"""Sample API Client."""

from __future__ import annotations

import json
import logging
import os
import socket
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import async_timeout
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_utc_time_change

from .const import (
    CONF_ENABLE_AUTODISCOVERY,
    CONF_LIBRARY_URL,
    DATA_LIBRARY_LAST_UPDATE,
    DEFAULT_LIBRARY_URL,
    DOMAIN,
    DOMAIN_CONFIG,
)
from .discovery import DiscoveryManager

_LOGGER = logging.getLogger(__name__)

BUILT_IN_DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "data")

class LibraryUpdaterClientError(Exception):
    """Exception to indicate a general API error."""


class LibraryUpdaterClientCommunicationError(LibraryUpdaterClientError):
    """Exception to indicate a communication error."""


class LibraryUpdater:
    """Library updater."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the library updater."""
        self.hass = hass

        if DOMAIN_CONFIG in self.hass.data[DOMAIN]:
            domain_config: dict = self.hass.data[DOMAIN][DOMAIN_CONFIG]
            url = domain_config.get(CONF_LIBRARY_URL, DEFAULT_LIBRARY_URL)
        else:
            url = DEFAULT_LIBRARY_URL

        self._client = LibraryUpdaterClient(library_url=url, session=async_get_clientsession(hass))

        # Fire the library check every 24 hours from just before now
        refresh_time = datetime.now() - timedelta(hours=0, minutes=1)
        async_track_utc_time_change(
            hass, self.timer_update, hour=refresh_time.hour, minute=refresh_time.minute, second=refresh_time.second, local=True
        )

    @callback
    async def timer_update(self, now: datetime):
        """Need to update the library."""
        if await self.time_to_update_library() is False:
            return

        await self.get_library_updates(now)

        if DOMAIN_CONFIG not in self.hass.data[DOMAIN]:
            return

        domain_config: dict = self.hass.data[DOMAIN][DOMAIN_CONFIG]

        if domain_config.get(CONF_ENABLE_AUTODISCOVERY):
            discovery_manager = DiscoveryManager(self.hass, domain_config)
            await discovery_manager.start_discovery()
        else:
            _LOGGER.debug("Auto discovery disabled")

    @callback
    async def get_library_updates(self, now: datetime):
        # pylint: disable=unused-argument
        """Make a call to GitHub to get the latest library.json."""

        def _update_library_json(library_file: str, content: str) -> None:
            with open(library_file, mode="w", encoding="utf-8") as file:
                file.write(content)
                file.close()

        try:
            _LOGGER.debug("Getting library updates")

            content = await self._client.async_get_data()

            if self.validate_json(content):
                json_path = os.path.join(
                    BUILT_IN_DATA_DIRECTORY,
                    "library.json",
                )

                await self.hass.async_add_executor_job(
                    _update_library_json, json_path, content
                )

                self.hass.data[DOMAIN][DATA_LIBRARY_LAST_UPDATE] = datetime.now()

                _LOGGER.debug("Updated library")
            else:
                _LOGGER.error("Library file is invalid, not updated")

        except LibraryUpdaterClientError:
            _LOGGER.warning(
                "Unable to update library, will retry later."
            )

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
        library_url: str,
        session: aiohttp.ClientSession,
    ) -> None:
        """Client to get latest library file from GitHub."""
        self._library_url = library_url
        self._session = session

    async def async_get_data(self) -> Any:
        """Get data from the API."""
        _LOGGER.debug(f"Updating library from {self._library_url}")
        return await self._api_wrapper(method="get", url=self._library_url)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
    ) -> Any:
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

        except TimeoutError as exception:
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

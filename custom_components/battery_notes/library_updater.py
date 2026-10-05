"""Library updater."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import socket
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import aiohttp

from homeassistant.const import CONTENT_TYPE_JSON
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_utc_time_change
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util import dt as dt_util

from .const import (
    DEFAULT_LIBRARY_URL,
    FALLBACK_LIBRARY_URL,
)
from .coordinator import MY_KEY
from .discovery import DiscoveryManager
from .library import DATA_LIBRARY

_LOGGER = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "BatteryNotes",
    "Content-Type": CONTENT_TYPE_JSON,
    "Accept-Encoding": "gzip",
}


class LibraryUpdaterClientError(Exception):
    """Exception to indicate a general API error."""


class LibraryUpdaterClientCommunicationError(LibraryUpdaterClientError):
    """Exception to indicate a communication error."""


class LibraryUpdater:
    """Library updater."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the library updater."""
        self.hass = hass
        self._update_lock = asyncio.Lock()

        self._client = LibraryUpdaterClient(session=async_get_clientsession(hass))

    @callback
    def async_start_daily_update(self) -> CALLBACK_TYPE:
        """Fire the library check every 24 hours from just before now, return the unsubscribe callback."""
        refresh_time = dt_util.utcnow() - timedelta(hours=0, minutes=1)
        return async_track_utc_time_change(
            self.hass,
            self.timer_update,
            hour=refresh_time.hour,
            minute=refresh_time.minute,
            second=refresh_time.second,
        )

    async def timer_update(self, now: datetime) -> None:  # noqa: ARG002
        """Need to update the library."""
        if await self.time_to_update_library(23) is False:
            return

        await self.get_library_updates()

        await self.hass.data[DATA_LIBRARY].load_libraries()

        domain_config = self.hass.data[MY_KEY]

        if domain_config and domain_config.enable_autodiscovery:
            discovery_manager = DiscoveryManager(self.hass, domain_config)
            await discovery_manager.start_discovery()
        else:
            _LOGGER.debug("Auto discovery disabled")

    async def get_library_updates(self, startup: bool = False) -> None:
        """Make a call to get the latest library.json."""
        async with self._update_lock:
            await self._do_get_library_updates(startup)

    async def _do_get_library_updates(self, startup: bool = False) -> None:
        """Get library updates internally (must be called with lock held)."""

        def _update_library_json(library_file: str, content: str) -> None:
            os.makedirs(os.path.dirname(library_file), exist_ok=True)
            # Write to a temporary file first so an interrupted write keeps the library
            temp_file = f"{library_file}.tmp"
            with open(temp_file, mode="w", encoding="utf-8") as file:
                file.write(content)
            Path(temp_file).replace(library_file)

        _LOGGER.debug("Getting library updates")

        try:
            content = await self._client.async_get_data(DEFAULT_LIBRARY_URL)
        except LibraryUpdaterClientError:
            # Try fallback URL
            _LOGGER.debug("Trying fallback library URL")
            try:
                content = await self._client.async_get_data(FALLBACK_LIBRARY_URL)
            except LibraryUpdaterClientError:
                if not startup:
                    _LOGGER.warning(
                        "Unable to update library from primary or fallback URLs, will retry later."
                    )
                return

        if self.validate_json(content):
            json_path = self.hass.config.path(
                STORAGE_DIR, "battery_notes", "library.json"
            )

            await self.hass.async_add_executor_job(
                _update_library_json, json_path, content
            )

            domain_config = self.hass.data.get(MY_KEY)
            if domain_config:
                self.hass.data[MY_KEY].library_last_update = dt_util.utcnow()

            _LOGGER.debug("Updated library")
        else:
            _LOGGER.error("Library file is invalid, please update Battery Notes")

    async def copy_schema(self):
        """Copy schema file to storage to be relative to downloaded library."""

        def _copy_schema(source: str, destination: str) -> None:
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            shutil.copyfile(source, destination)

        install_schema_path = os.path.join(os.path.dirname(__file__), "schema.json")
        storage_schema_path = self.hass.config.path(
            STORAGE_DIR, "battery_notes", "schema.json"
        )
        await self.hass.async_add_executor_job(
            _copy_schema,
            install_schema_path,
            storage_schema_path,
        )

    async def time_to_update_library(self, hours: int) -> bool:
        """Check when last updated and if OK to do a new library update."""
        try:
            domain_config = self.hass.data.get(MY_KEY)
            if not domain_config:
                return True

            if library_last_update := self.hass.data[MY_KEY].library_last_update:
                time_since_last_update = dt_util.utcnow() - library_last_update

                time_difference_in_hours = time_since_last_update / timedelta(hours=1)

                if time_difference_in_hours < hours:
                    _LOGGER.debug("Skipping library update, too recent")
                    return False

            return True
        except ConfigEntryNotReady:
            # Ignore as we are initial load
            return True

    def validate_json(self, content: str) -> bool:
        """Check if content is a library this version can use."""
        try:
            library = json.loads(content)
        except ValueError:
            return False

        return (
            isinstance(library, dict)
            and isinstance(library.get("version"), int)
            and library["version"] <= 1
            and isinstance(library.get("devices"), list)
            and len(library["devices"]) > 0
        )


class LibraryUpdaterClient:
    """Library downloader."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        """Client to get latest library file from GitHub."""
        self._session = session

    async def async_get_data(self, url: str) -> Any:
        """Get data from the API."""
        _LOGGER.debug("Updating library from %s", url)
        return await self._api_wrapper(method="get", url=url, headers=HEADERS)

    async def _api_wrapper(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
    ) -> Any:
        """Get information from the API."""
        try:
            async with (
                asyncio.timeout(10),
                self._session.request(
                    method=method,
                    url=url,
                    allow_redirects=True,
                    headers=headers,
                ) as response,
            ):
                if response.status != 200:
                    raise LibraryUpdaterClientCommunicationError(  # noqa: TRY301
                        f"HTTP {response.status} error fetching information",
                    )
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

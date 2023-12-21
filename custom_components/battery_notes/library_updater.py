"""Sample API Client."""
from __future__ import annotations

import asyncio
import socket

import aiohttp
import async_timeout

from .const import CONF_LIBRARY_URL


class LibraryUpdaterClientError(Exception):
    """Exception to indicate a general API error."""


class LibraryUpdaterClientCommunicationError(LibraryUpdaterClientError):
    """Exception to indicate a communication error."""


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

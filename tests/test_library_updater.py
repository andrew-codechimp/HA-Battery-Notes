"""Tests for library downloads and scheduled updates."""

import asyncio
import socket
from collections.abc import Generator
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, call, patch

import aiohttp
import pytest
from custom_components.battery_notes.const import (
    DEFAULT_LIBRARY_URL,
    FALLBACK_LIBRARY_URL,
)
from custom_components.battery_notes.coordinator import MY_KEY, BatteryNotesDomainConfig
from custom_components.battery_notes.library import DATA_LIBRARY, Library
from custom_components.battery_notes.library_updater import (
    HEADERS,
    LibraryUpdater,
    LibraryUpdaterClient,
    LibraryUpdaterClientCommunicationError,
    LibraryUpdaterClientError,
)
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    async_fire_time_changed,
    load_fixture,
)

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import STORAGE_DIR
from homeassistant.util import dt as dt_util


@pytest.fixture(autouse=True)
def mock_library_client() -> Generator[MagicMock]:
    """Mock the downloader using the Mealie client fixture pattern."""
    with patch(
        "custom_components.battery_notes.library_updater.LibraryUpdaterClient",
        autospec=True,
    ) as mock_client:
        client = mock_client.return_value
        client.async_get_data.return_value = load_fixture("library.json")
        yield client


@pytest.fixture
async def updater(hass: HomeAssistant, tmp_path: Path) -> LibraryUpdater:
    """Create an updater with isolated storage and real domain configuration."""
    hass.config.config_dir = str(tmp_path)
    hass.data[MY_KEY] = BatteryNotesDomainConfig()
    return LibraryUpdater(hass)


@pytest.mark.parametrize(
    "fallback",
    [pytest.param(False, id="primary"), pytest.param(True, id="fallback")],
)
@pytest.mark.usefixtures("freezer")
async def test_download_library(
    hass: HomeAssistant,
    updater: LibraryUpdater,
    mock_library_client: MagicMock,
    fallback: bool,
) -> None:
    """Test successful downloads persist content and the last update time."""
    content = load_fixture("library.json")
    mock_library_client.async_get_data.side_effect = {
        False: [content],
        True: [LibraryUpdaterClientCommunicationError, content],
    }[fallback]

    await updater.get_library_updates()

    assert (
        mock_library_client.async_get_data.await_args_list
        == {
            False: [call(DEFAULT_LIBRARY_URL)],
            True: [call(DEFAULT_LIBRARY_URL), call(FALLBACK_LIBRARY_URL)],
        }[fallback]
    )
    library_path = Path(hass.config.path(STORAGE_DIR, "battery_notes", "library.json"))
    assert await hass.async_add_executor_job(library_path.read_text) == content
    assert hass.data[MY_KEY].library_last_update == dt_util.utcnow()
    library = Library(hass)
    await library.load_libraries()
    assert library.is_loaded


@pytest.mark.usefixtures("mock_library_client")
async def test_download_without_domain_config(
    hass: HomeAssistant,
    updater: LibraryUpdater,
) -> None:
    """Test initial downloads succeed before domain configuration is available."""
    del hass.data[MY_KEY]

    await updater.get_library_updates(startup=True)

    library_path = Path(hass.config.path(STORAGE_DIR, "battery_notes", "library.json"))
    assert await hass.async_add_executor_job(library_path.read_text) == load_fixture(
        "library.json"
    )
    assert MY_KEY not in hass.data


@pytest.mark.parametrize(
    "startup",
    [
        pytest.param(True, id="startup"),
        pytest.param(False, id="scheduled"),
    ],
)
async def test_download_failure(
    hass: HomeAssistant,
    updater: LibraryUpdater,
    mock_library_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
    startup: bool,
) -> None:
    """Test both failed URLs leave the existing library and timestamp intact."""
    await updater.get_library_updates()
    last_update = hass.data[MY_KEY].library_last_update
    mock_library_client.async_get_data.reset_mock()
    mock_library_client.async_get_data.side_effect = LibraryUpdaterClientError

    await updater.get_library_updates(startup=startup)

    assert mock_library_client.async_get_data.await_args_list == [
        call(DEFAULT_LIBRARY_URL),
        call(FALLBACK_LIBRARY_URL),
    ]
    assert caplog.text.count("Unable to update library") == int(not startup)
    assert hass.data[MY_KEY].library_last_update == last_update
    library_path = Path(hass.config.path(STORAGE_DIR, "battery_notes", "library.json"))
    assert await hass.async_add_executor_job(library_path.read_text) == load_fixture(
        "library.json"
    )


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("invalid json", id="malformed"),
        pytest.param('{"devices": []}', id="missing-version"),
        pytest.param('{"version": 2}', id="unsupported-version"),
    ],
)
async def test_invalid_download(
    hass: HomeAssistant,
    updater: LibraryUpdater,
    mock_library_client: MagicMock,
    caplog: pytest.LogCaptureFixture,
    content: str,
) -> None:
    """Test invalid downloads preserve the last valid library."""
    await updater.get_library_updates()
    last_update = hass.data[MY_KEY].library_last_update
    mock_library_client.async_get_data.return_value = content

    await updater.get_library_updates()

    assert "Library file is invalid" in caplog.text
    assert hass.data[MY_KEY].library_last_update == last_update
    library_path = Path(hass.config.path(STORAGE_DIR, "battery_notes", "library.json"))
    assert await hass.async_add_executor_job(library_path.read_text) == load_fixture(
        "library.json"
    )


async def test_copy_schema(hass: HomeAssistant, updater: LibraryUpdater) -> None:
    """Test schema copying creates storage directories and preserves its content."""
    await updater.copy_schema()

    source = Path(__file__).parents[1] / "custom_components/battery_notes/schema.json"
    destination = Path(hass.config.path(STORAGE_DIR, "battery_notes", "schema.json"))
    assert await hass.async_add_executor_job(
        destination.read_bytes
    ) == await hass.async_add_executor_job(source.read_bytes)


@pytest.mark.parametrize(
    ("elapsed", "expected"),
    [
        pytest.param(None, True, id="never-updated"),
        pytest.param(timedelta(hours=22, minutes=59), False, id="recent"),
        pytest.param(timedelta(hours=23), True, id="exact-boundary"),
        pytest.param(timedelta(hours=24), True, id="overdue"),
    ],
)
@pytest.mark.usefixtures("freezer")
async def test_update_interval(
    hass: HomeAssistant,
    updater: LibraryUpdater,
    elapsed: timedelta | None,
    expected: bool,
) -> None:
    """Test the update interval includes the exact cutoff."""
    hass.data[MY_KEY].library_last_update = (
        dt_util.utcnow() - elapsed if elapsed is not None else None
    )
    assert await updater.time_to_update_library(23) is expected


async def test_update_interval_without_config(
    hass: HomeAssistant, updater: LibraryUpdater
) -> None:
    """Test the library can be updated without domain configuration."""
    del hass.data[MY_KEY]
    assert await updater.time_to_update_library(23)


async def test_update_interval_config_not_ready(updater: LibraryUpdater) -> None:
    """Test an initial load does not prevent downloading the library."""
    with patch.object(
        BatteryNotesDomainConfig,
        "library_last_update",
        new_callable=PropertyMock,
        side_effect=ConfigEntryNotReady,
    ):
        assert await updater.time_to_update_library(23)


@pytest.mark.parametrize(
    "enable_autodiscovery",
    [pytest.param(True, id="enabled"), pytest.param(False, id="disabled")],
)
async def test_daily_update(
    hass: HomeAssistant,
    updater: LibraryUpdater,
    mock_library_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    enable_autodiscovery: bool,
) -> None:
    """Test daily scheduling downloads, reloads, discovers, and unsubscribes."""
    freezer.move_to("2026-06-01 12:00:30+00:00")
    hass.data[MY_KEY].enable_autodiscovery = enable_autodiscovery
    library = Library(hass)
    hass.data[DATA_LIBRARY] = library
    with patch(
        "custom_components.battery_notes.library_updater.DiscoveryManager",
        autospec=True,
    ) as manager:
        unsubscribe = updater.async_start_daily_update()
        freezer.tick(timedelta(hours=23, minutes=59))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)

        mock_library_client.async_get_data.assert_awaited_once_with(DEFAULT_LIBRARY_URL)
        assert library.is_loaded
        assert manager.call_count == int(enable_autodiscovery)
        assert manager.return_value.start_discovery.await_count == int(
            enable_autodiscovery
        )
        assert (
            manager.call_args_list
            == {
                True: [call(hass, hass.data[MY_KEY])],
                False: [],
            }[enable_autodiscovery]
        )

        unsubscribe()
        freezer.tick(timedelta(days=1))
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done(wait_background_tasks=True)
        assert mock_library_client.async_get_data.await_count == 1


@pytest.mark.usefixtures("mock_library_client", "freezer")
async def test_timer_skips_recent_update(
    hass: HomeAssistant, updater: LibraryUpdater
) -> None:
    """Test a recent update skips downloads and library loading."""
    hass.data[MY_KEY].library_last_update = dt_util.utcnow()
    with patch.object(updater, "get_library_updates") as download:
        await updater.timer_update(dt_util.utcnow())
    download.assert_not_awaited()


async def test_concurrent_downloads(
    updater: LibraryUpdater, mock_library_client: MagicMock
) -> None:
    """Test concurrent requests cannot download or write the library together."""
    started = asyncio.Event()
    release = asyncio.Event()

    async def download(_url: str) -> str:
        started.set()
        await release.wait()
        return load_fixture("library.json")

    mock_library_client.async_get_data.side_effect = download
    first = asyncio.create_task(updater.get_library_updates())
    await started.wait()
    second = asyncio.create_task(updater.get_library_updates())
    await asyncio.sleep(0)
    assert mock_library_client.async_get_data.await_count == 1
    release.set()
    await asyncio.gather(first, second)
    assert mock_library_client.async_get_data.await_count == 2


async def test_client_download() -> None:
    """Test the client passes download headers and returns response text."""
    session = MagicMock(spec=aiohttp.ClientSession)
    session.request = AsyncMock()
    session.request.return_value.status = 200
    session.request.return_value.text = AsyncMock(
        return_value=load_fixture("library.json")
    )
    client = LibraryUpdaterClient(session)

    assert await client.async_get_data(DEFAULT_LIBRARY_URL) == load_fixture(
        "library.json"
    )
    session.request.assert_awaited_once_with(
        method="get", url=DEFAULT_LIBRARY_URL, allow_redirects=True, headers=HEADERS
    )


@pytest.mark.parametrize(
    ("exception", "expected_type", "message"),
    [
        pytest.param(
            TimeoutError(),
            LibraryUpdaterClientCommunicationError,
            "Timeout error fetching information",
            id="timeout",
        ),
        pytest.param(
            aiohttp.ClientError(),
            LibraryUpdaterClientCommunicationError,
            "Error fetching information",
            id="client-error",
        ),
        pytest.param(
            socket.gaierror(),
            LibraryUpdaterClientCommunicationError,
            "Error fetching information",
            id="dns-error",
        ),
        pytest.param(
            RuntimeError(),
            LibraryUpdaterClientError,
            "Something really wrong happened!",
            id="unexpected-error",
        ),
    ],
)
async def test_client_failure(
    hass: HomeAssistant,
    exception: Exception,
    expected_type: type[LibraryUpdaterClientError],
    message: str,
) -> None:
    """Test transport failures retain their cause and expose the expected error."""
    session = async_get_clientsession(hass)
    client = LibraryUpdaterClient(session)
    with (
        patch.object(session, "request", side_effect=exception),
        pytest.raises(expected_type, match=message) as raised,
    ):
        await client.async_get_data(DEFAULT_LIBRARY_URL)
    assert raised.value.__cause__ is exception


@pytest.mark.parametrize(
    "status", [pytest.param(404, id="not-found"), pytest.param(500, id="server-error")]
)
async def test_client_http_failure(hass: HomeAssistant, status: int) -> None:
    """Test unsuccessful HTTP responses are rejected before reading content."""
    session = async_get_clientsession(hass)
    response = MagicMock(spec=aiohttp.ClientResponse)
    response.status = status
    client = LibraryUpdaterClient(session)
    with (
        patch.object(session, "request", new=AsyncMock(return_value=response)),
        pytest.raises(LibraryUpdaterClientError) as raised,
    ):
        await client.async_get_data(DEFAULT_LIBRARY_URL)
    assert isinstance(raised.value.__cause__, LibraryUpdaterClientCommunicationError)
    assert str(raised.value.__cause__) == f"HTTP {status} error fetching information"
    response.text.assert_not_called()

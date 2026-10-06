"""Tests for migrating legacy Battery Notes config entries."""

import pytest
from custom_components.battery_notes.const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    DOMAIN,
    SUBENTRY_BATTERY_NOTE,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.setup import async_setup_component

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")


@pytest.mark.parametrize(
    ("version", "battery_type", "expected"),
    [
        pytest.param(1, "2x AA", ("AA", 2), id="v1-quantity-and-type"),
        pytest.param(1, "CR2032", ("CR2032", 1), id="v1-type-only"),
        pytest.param(
            1, "2x Rechargeable cell", ("2x Rechargeable cell", 1), id="v1-unsplittable"
        ),
        pytest.param(2, "AAA", ("AAA", 3), id="v2"),
    ],
)
async def test_migrate_legacy_entry(
    hass: HomeAssistant,
    battery_note_device: dr.DeviceEntry,
    version: int,
    battery_type: str,
    expected: tuple[str, int],
) -> None:
    """Test legacy per-device entries become battery note subentries."""
    data = {CONF_DEVICE_ID: battery_note_device.id, CONF_BATTERY_TYPE: battery_type}
    if version == 2:
        data[CONF_BATTERY_QUANTITY] = 3
    MockConfigEntry(
        domain=DOMAIN,
        version=version,
        title="Door sensor",
        unique_id=f"bn_{battery_note_device.id}",
        data=data,
    ).add_to_hass(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1
    assert entries[0].version == 4
    subentries = list(entries[0].get_subentries_of_type(SUBENTRY_BATTERY_NOTE))
    assert len(subentries) == 1
    assert subentries[0].unique_id == f"bn_{battery_note_device.id}"
    assert (
        subentries[0].data[CONF_BATTERY_TYPE],
        subentries[0].data[CONF_BATTERY_QUANTITY],
    ) == expected
    assert CONF_ADVANCED_SETTINGS in subentries[0].data

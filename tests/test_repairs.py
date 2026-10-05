"""Tests for Battery Notes repairs."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from custom_components.battery_notes.common import composite_device_issue_id
from custom_components.battery_notes.const import DOMAIN
from custom_components.battery_notes.repairs import CompositeDeviceIdRepairFlow
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr, issue_registry as ir

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")


@pytest.fixture
def composite_device_id(battery_note_device: dr.DeviceEntry) -> Generator[str]:
    """Treat the source device as a legacy composite device."""
    with patch(
        "custom_components.battery_notes.is_composite_device_id",
        side_effect=lambda _hass, device_id: device_id == battery_note_device.id,
    ):
        yield battery_note_device.id


@pytest.mark.usefixtures("composite_device_id")
async def test_composite_device_issue(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_source: str,
) -> None:
    """Test only device notes on a composite device ask to select a device again."""
    await setup_integration(hass, battery_note_config_entry)
    subentry = next(iter(battery_note_config_entry.subentries.values()))

    issue = ir.async_get(hass).async_get_issue(
        DOMAIN, composite_device_issue_id(subentry.subentry_id)
    )

    assert (issue is not None) is (battery_note_source == "device")


@pytest.mark.parametrize("battery_note_source", ["device"])
async def test_composite_device_repair(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    composite_device_id: str,
) -> None:
    """Test selecting a split device relinks the note with a single reload."""
    await setup_integration(hass, battery_note_config_entry)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    issue_id = composite_device_issue_id(subentry.subentry_id)
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None
    split_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=next(iter(battery_note_device.config_entries)),
        identifiers={("test", "split-door-sensor")},
        name="Door sensor",
    )
    flow = CompositeDeviceIdRepairFlow(battery_note_config_entry, subentry)
    flow.hass = hass
    flow.handler = DOMAIN
    flow.flow_id = "repair"

    with patch.object(
        hass.config_entries, "async_reload", wraps=hass.config_entries.async_reload
    ) as reload_entry:
        result = await flow.async_step_select_device({CONF_DEVICE_ID: split_device.id})
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert reload_entry.call_count == 1
    subentry = battery_note_config_entry.subentries[subentry.subentry_id]
    assert subentry.data[CONF_DEVICE_ID] == split_device.id
    assert composite_device_id != split_device.id
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

"""Tests for Battery Notes repairs."""

from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from custom_components.battery_notes.common import composite_device_issue_id
from custom_components.battery_notes.const import (
    DOMAIN,
    LAST_REPLACED,
    LAST_REPORTED,
    LAST_REPORTED_LEVEL,
)
from custom_components.battery_notes.repairs import CompositeDeviceIdRepairFlow
from custom_components.battery_notes.store import async_get_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.const import ATTR_DEVICE_ID, CONF_DEVICE_ID, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import (
    device_registry as dr,
    entity_registry as er,
    issue_registry as ir,
)

from . import setup_integration

pytestmark = pytest.mark.usefixtures("mock_library_updater", "_mock_library_file")


@pytest.fixture
def composite_device_id(battery_note_device: dr.DeviceEntry) -> Generator[str]:
    """Treat the source device as a legacy composite device."""
    with (
        patch(
            "custom_components.battery_notes.is_composite_device_id",
            side_effect=lambda _hass, device_id: device_id == battery_note_device.id,
        ),
        patch(
            "custom_components.battery_notes.entity.is_composite_device_id",
            side_effect=lambda _hass, device_id: device_id == battery_note_device.id,
        ),
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


@pytest.mark.parametrize("battery_note_source", ["entity"])
@pytest.mark.parametrize("source_device", ["split", "standalone"])
@pytest.mark.usefixtures("composite_device_id")
async def test_composite_entity_note_uses_current_device(
    hass: HomeAssistant,
    battery_note_config_entry: MockConfigEntry,
    battery_note_device: dr.DeviceEntry,
    battery_note_sensor: er.RegistryEntry,
    source_device: str,
) -> None:
    """Test entity notes follow a split source device without losing history."""
    split_device = dr.async_get(hass).async_get_or_create(
        config_entry_id=next(iter(battery_note_device.config_entries)),
        identifiers={("test", "split-door-sensor")},
        name="Door sensor",
    )
    current_device_id = {"split": split_device.id, "standalone": None}[source_device]
    entity_registry = er.async_get(hass)
    entity_registry.async_update_entity(
        battery_note_sensor.entity_id, device_id=current_device_id
    )
    # Keep the source unavailable so setup cannot replace its stored report.
    hass.states.async_set(battery_note_sensor.entity_id, STATE_UNAVAILABLE)
    store = await async_get_registry(hass)
    history = {
        LAST_REPLACED: datetime(2025, 12, 1, tzinfo=UTC),
        LAST_REPORTED: datetime(2026, 1, 1, tzinfo=UTC),
        LAST_REPORTED_LEVEL: 55.0,
    }
    store.async_create_entity(battery_note_sensor.entity_id, history)

    await setup_integration(hass, battery_note_config_entry)
    subentry = next(iter(battery_note_config_entry.subentries.values()))
    coordinator = battery_note_config_entry.runtime_data.subentry_coordinators[
        subentry.subentry_id
    ]

    assert subentry.data[CONF_DEVICE_ID] == battery_note_device.id
    assert coordinator.device_id == current_device_id
    assert coordinator.event_data()[ATTR_DEVICE_ID] == (current_device_id or "")
    assert (
        ir.async_get(hass).async_get_issue(
            DOMAIN, composite_device_issue_id(subentry.subentry_id)
        )
        is None
    )
    for domain, suffix in (
        ("sensor", "battery_plus"),
        ("binary_sensor", "battery_low"),
    ):
        entity_id = entity_registry.async_get_entity_id(
            domain, DOMAIN, f"{subentry.unique_id}_{suffix}"
        )
        assert entity_id is not None
        assert entity_registry.async_get(entity_id).device_id == current_device_id
    assert store.async_get_entity(battery_note_sensor.entity_id) == {
        "entity_id": battery_note_sensor.entity_id,
        **history,
    }
    assert coordinator.last_replaced == history[LAST_REPLACED]
    assert coordinator.last_reported == history[LAST_REPORTED]
    assert coordinator.last_reported_level == history[LAST_REPORTED_LEVEL]


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

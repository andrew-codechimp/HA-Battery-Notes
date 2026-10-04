"""Tests for common helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from custom_components.battery_notes import common
from custom_components.battery_notes.const import CONF_SOURCE_ENTITY_ID, DOMAIN

from homeassistant.const import CONF_DEVICE_ID
from homeassistant.helpers import entity_registry as er


def _entry(
    entity_id: str,
    device_class: str | None = "battery",
    hidden_by: er.RegistryEntryHider | None = er.RegistryEntryHider.INTEGRATION,
    platform: str = "zha",
) -> MagicMock:
    entry = MagicMock()
    entry.entity_id = entity_id
    entry.device_class = None
    entry.original_device_class = device_class
    entry.hidden_by = hidden_by
    entry.platform = platform
    return entry


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Mock the entity registry with a set of device entities."""
    device_entities = [
        _entry("sensor.lock_battery"),
        _entry("binary_sensor.lock_battery_low"),
        _entry("sensor.lock_battery_user_hidden", hidden_by=er.RegistryEntryHider.USER),
        _entry("sensor.lock_temperature", device_class="temperature"),
        _entry("sensor.lock_battery_plus", platform=DOMAIN),
    ]
    registry = MagicMock()
    registry.async_get.side_effect = lambda entity_id: next(
        (e for e in device_entities if e.entity_id == entity_id), None
    )
    monkeypatch.setattr(common.er, "async_get", lambda _hass: registry)
    monkeypatch.setattr(
        common.er,
        "async_entries_for_device",
        lambda _registry, device_id, **_kwargs: (
            device_entities if device_id == "lock" else []
        ),
    )
    return registry


def _unhidden(registry: MagicMock) -> list[str]:
    return [
        call.args[0]
        for call in registry.async_update_entity.call_args_list
        if call.kwargs == {"hidden_by": None}
    ]


def test_unhide_device_batteries(registry: MagicMock) -> None:
    """Only battery entities hidden by an integration are shown again."""
    common.async_unhide_source_batteries(MagicMock(), {CONF_DEVICE_ID: "lock"})

    assert _unhidden(registry) == [
        "sensor.lock_battery",
        "binary_sensor.lock_battery_low",
    ]


def test_unhide_source_entity(registry: MagicMock) -> None:
    """A battery note for an entity only shows that entity again."""
    common.async_unhide_source_batteries(
        MagicMock(),
        {
            CONF_DEVICE_ID: "lock",
            CONF_SOURCE_ENTITY_ID: "binary_sensor.lock_battery_low",
        },
    )

    assert _unhidden(registry) == ["binary_sensor.lock_battery_low"]


def test_unhide_missing_source(registry: MagicMock) -> None:
    """A missing source entity or device is ignored."""
    common.async_unhide_source_batteries(
        MagicMock(), {CONF_SOURCE_ENTITY_ID: "sensor.missing"}
    )
    common.async_unhide_source_batteries(MagicMock(), {CONF_DEVICE_ID: "missing"})
    common.async_unhide_source_batteries(MagicMock(), {})

    assert _unhidden(registry) == []

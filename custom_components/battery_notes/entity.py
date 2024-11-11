"""Entity for battery_notes."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription


@dataclass(frozen=True, kw_only=True)
class BatteryNotesRequiredKeysMixin:
    """Mixin for required keys."""

    unique_id_suffix: str


@dataclass(frozen=True, kw_only=True)
class BatteryNotesEntityDescription(EntityDescription, BatteryNotesRequiredKeysMixin):
    """Generic Battery Notes entity description."""

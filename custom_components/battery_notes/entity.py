"""Entity for battery_notes."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.helpers.entity import EntityDescription

@dataclass
class BatteryNotesRequiredKeysMixin:
    """Mixin for required keys."""

    unique_id_suffix: str


@dataclass
class BatteryNotesEntityDescription(EntityDescription, BatteryNotesRequiredKeysMixin):
    """Generic Battery Notes entity description."""

"""Diagnostic helpers."""

from homeassistant.config_entries import ConfigEntry


async def async_get_config_entry_diagnostics(
    entry: ConfigEntry,
) -> dict:
    """Return diagnostics for a config entry."""
    return {
        "entry": entry.as_dict(),
    }

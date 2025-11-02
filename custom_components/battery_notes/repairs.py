"""Repairs for battery_notes."""

from __future__ import annotations

from typing import cast

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.components.repairs import RepairsFlow

REQUIRED_KEYS = ("entry_id", "device_id", "source_entity_id")


class MissingDeviceRepairFlow(RepairsFlow):
    """Handler for an issue fixing flow."""

    def __init__(self, data: dict[str, str | int | float | None] | None) -> None:
        """Initialize."""
        if not data or any(key not in data for key in REQUIRED_KEYS):
            raise ValueError("Missing data")
        self.entry_id = cast(str, data["entry_id"])
        self.subentry_id = cast(str, data["subentry_id"])
        self.device_id = cast(str, data["device_id"])
        self.source_entity_id = cast(str, data["source_entity_id"])

    async def async_step_init(
        self,
        user_input: dict[str, str] | None = None,  # noqa: ARG002
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the confirm step of a fix flow."""
        if user_input is not None:
            if entry := self.hass.config_entries.async_get_entry(self.entry_id):
                self.hass.config_entries.async_remove_subentry(entry, self.subentry_id)

            return self.async_create_entry(data={})

        issue_registry = ir.async_get(self.hass)
        description_placeholders = None
        if issue := issue_registry.async_get_issue(self.handler, self.issue_id):
            description_placeholders = issue.translation_placeholders

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders=description_placeholders,
        )


async def async_create_fix_flow(
    hass: HomeAssistant,  # noqa: ARG001
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id.startswith("missing_device_"):
        assert data

        return MissingDeviceRepairFlow(data)
    raise ValueError(f"unknown repair {issue_id}")

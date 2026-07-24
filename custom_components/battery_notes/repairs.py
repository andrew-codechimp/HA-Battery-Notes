"""Repairs for battery_notes."""

from __future__ import annotations

import logging
from typing import cast

import voluptuous as vol

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, issue_registry as ir
from homeassistant.helpers.selector import DeviceSelector

from .const import DOMAIN
from .store import async_get_registry

REQUIRED_KEYS = ("entry_id", "device_id", "source_entity_id")

_LOGGER = logging.getLogger(__name__)


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


class CompositeDeviceIdRepairFlow(RepairsFlow):
    """Handler to select a device again after the linked device was split."""

    def __init__(self, entry: ConfigEntry, subentry: ConfigSubentry) -> None:
        """Initialize the flow."""
        self._entry = entry
        self._subentry = subentry

    async def async_step_init(
        self,
        user_input: dict[str, str] | None = None,  # noqa: ARG002
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of the fix flow."""
        return await self.async_step_select_device()

    async def async_step_select_device(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the device selection step."""

        errors: dict[str, str] = {}

        device_registry = dr.async_get(self.hass)
        if user_input is not None:
            device_id = user_input.get(CONF_DEVICE_ID)
            old_device_id = self._subentry.data[CONF_DEVICE_ID]
            store = await async_get_registry(self.hass)

            if device_id is None or device_id == old_device_id:
                self.hass.config_entries.async_remove_subentry(
                    self._entry, self._subentry.subentry_id
                )
                store.async_delete_device(old_device_id)
                return self.async_abort(reason="entry_removed")  # type: ignore[no-any-return]

            if device_registry.async_get(device_id) is None:
                errors["base"] = "invalid_device"

            if not errors:
                try:
                    store.async_change_device_id(old_device_id, device_id)
                except ValueError:
                    errors["base"] = "invalid_device"

            if not errors:
                data = {**self._subentry.data}
                data[CONF_DEVICE_ID] = device_id
                self.hass.config_entries.async_update_subentry(
                    self._entry, self._subentry, data=data
                )
                ir.async_delete_issue(
                    self.hass,
                    DOMAIN,
                    f"composite_device_id_{self._subentry.subentry_id}",
                )
                await self.hass.config_entries.async_reload(self._entry.entry_id)
                return self.async_create_entry(data={})

        old_device_id = self._subentry.data[CONF_DEVICE_ID]
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICE_ID,
                        description={"suggested_value": old_device_id},
                    ): DeviceSelector(),
                }
            ),
            errors=errors,
            description_placeholders={
                "name": self._subentry.title,
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None,
) -> RepairsFlow:
    """Create flow."""
    if issue_id.startswith("missing_device_"):
        assert data

        return MissingDeviceRepairFlow(data)
    if (
        issue_id.startswith("composite_device_id_")
        and data is not None
        and (entry := hass.config_entries.async_get_entry(str(data["entry_id"])))
        is not None
        and (subentry := entry.subentries.get(str(data["subentry_id"]))) is not None
    ):
        return CompositeDeviceIdRepairFlow(entry, subentry)
    raise HomeAssistantError(f"Unknown issue {issue_id}")

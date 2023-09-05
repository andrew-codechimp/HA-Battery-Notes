"""Adds config flow for BatteryNotes."""
from __future__ import annotations

import copy
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.helpers import selector
import homeassistant.helpers.device_registry as dr

from homeassistant.const import CONF_NAME

from .const import DOMAIN, CONF_DEVICE_ID, CONF_BATTERY_TYPE

class BatteryNotesFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BatteryNotes."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]

            device_registry = dr.async_get(self.hass)
            device_entry = (
                device_registry.async_get(device_id)
            )

            unique_id = f"bn_{device_id}"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            if CONF_NAME in user_input:
                title = user_input.get(CONF_NAME)
            else:
                title = device_entry.name_by_user or device_entry.name

            return self.async_create_entry(
                title=title,
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE_ID,
                        default=(user_input or {}).get(CONF_DEVICE_ID)
                    ): selector.DeviceSelector(
                        # selector.DeviceSelectorConfig(model="otgw-nodo")
                    ),
                    vol.Optional(
                        CONF_NAME
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_TYPE,
                        default=(user_input or {}).get(CONF_BATTERY_TYPE),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                }
            ),
            errors=_errors,
        )

class OptionsFlowHandler(OptionsFlow):
    """Handle an option flow for BatteryNotes."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.current_config: dict = dict(config_entry.data)
        self.source_device_id: str = self.current_config.get(CONF_DEVICE_ID)  # type: ignore
        self.name: str = self.current_config.get(CONF_NAME)
        self.battery_type: str = self.current_config.get(CONF_BATTERY_TYPE)

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle options flow."""
        errors = {}
        self.current_config = dict(self.config_entry.data)

        schema = self.build_options_schema()
        if user_input is not None:
            errors = await self.save_options(user_input, schema)
            if not errors:
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )

    async def save_options(
        self,
        user_input: dict[str, Any],
        schema: vol.Schema,
    ) -> dict:
        """Save options, and return errors when validation fails."""
        device_registry = dr.async_get(self.hass)
        device_entry = (
            device_registry.async_get(self.config_entry.data.get(CONF_DEVICE_ID))
        )

        if CONF_NAME in user_input:
            title = user_input.get(CONF_NAME)
        else:
            title = device_entry.name_by_user or device_entry.name

        self._process_user_input(user_input, schema)
        self.hass.config_entries.async_update_entry(
            self.config_entry,
            title=title,
            data=self.current_config,
        )
        return {}

    def _process_user_input(
        self,
        user_input: dict[str, Any],
        schema: vol.Schema,
    ) -> None:
        """Process the provided user input against the schema."""
        for key in schema.schema:
            if isinstance(key, vol.Marker):
                key = key.schema
            if key in user_input:
                self.current_config[key] = user_input.get(key)
            elif key in self.current_config:
                self.current_config.pop(key)

    def build_options_schema(self) -> vol.Schema:
        """Build the options schema."""
        data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NAME
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_TYPE
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                }
            )

        return _fill_schema_defaults(
            data_schema,
            self.current_config,
        )

def _fill_schema_defaults(
    data_schema: vol.Schema,
    options: dict[str, str],
) -> vol.Schema:
    """Make a copy of the schema with suggested values set to saved options."""
    schema = {}
    for key, val in data_schema.schema.items():
        new_key = key
        if key in options and isinstance(key, vol.Marker):
            if (
                isinstance(key, vol.Optional)
                and callable(key.default)
                and key.default()
            ):
                new_key = vol.Optional(key.schema, default=options.get(key))  # type: ignore
            else:
                new_key = copy.copy(key)
                new_key.description = {"suggested_value": options.get(key)}  # type: ignore
        schema[new_key] = val
    return vol.Schema(schema)

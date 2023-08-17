"""Adds config flow for BatteryTypes."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector, device_registry
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import (
    BatteryTypesApiClient,
    BatteryTypesApiClientAuthenticationError,
    BatteryTypesApiClientCommunicationError,
    BatteryTypesApiClientError,
)
from .const import DOMAIN, LOGGER, CONF_DEVICE, CONF_BATTERY_TYPE


class BatteryTypesFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BatteryTypes."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            # registry = await self.hass.helpers.device_registry.async_get_registry()
            # device = registry.async_get_device({(DOMAIN, entry.data.get("mac"))}, set())

            # try:
            #     await self._test_credentials(
            #         username=user_input[CONF_USERNAME],
            #         password=user_input[CONF_PASSWORD],
            #     )
            # except BatteryTypesApiClientAuthenticationError as exception:
            #     LOGGER.warning(exception)
            #     _errors["base"] = "auth"
            # except BatteryTypesApiClientCommunicationError as exception:
            #     LOGGER.error(exception)
            #     _errors["base"] = "connection"
            # except BatteryTypesApiClientError as exception:
            #     LOGGER.exception(exception)
            #     _errors["base"] = "unknown"
            # else:
            return self.async_create_entry(
                title=user_input[CONF_DEVICE],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DEVICE, default=(user_input or {}).get(CONF_DEVICE)
                    ): selector.DeviceSelector(
                        # selector.DeviceSelectorConfig(model="otgw-nodo")
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

    async def _test_credentials(self, username: str, password: str) -> None:
        """Validate credentials."""
        client = BatteryTypesApiClient(
            username=username,
            password=password,
            session=async_create_clientsession(self.hass),
        )
        await client.async_get_data()

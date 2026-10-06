"""Adds config flow for BatteryNotes."""

from __future__ import annotations

import copy
import logging
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

import voluptuous as vol

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from homeassistant import config_entries
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback, split_entity_id
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
from homeassistant.helpers.typing import DiscoveryInfoType

from .common import get_device_model_id
from .const import (
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_PERCENTAGE_TEMPLATE,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_DEVICE_NAME,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_ENABLE_REPLACED,
    CONF_FILTER_OUTLIERS,
    CONF_HIDE_BATTERY,
    CONF_HIDE_BATTERY_LOW,
    CONF_HW_VERSION,
    CONF_INTEGRATION_NAME,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_MODEL_ID,
    CONF_NOTE,
    CONF_RETAIN_STATE,
    CONF_ROUND_BATTERY,
    CONF_SHOW_ALL_DEVICES,
    CONF_SOURCE_ENTITY_ID,
    CONF_USER_LIBRARY,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    DOMAIN,
    NAME as INTEGRATION_NAME,
    SUBENTRY_BATTERY_NOTE,
)
from .coordinator import MY_KEY
from .library import DATA_LIBRARY, DeviceBatteryDetails, ModelInfo
from .library_updater import LibraryUpdater

_LOGGER = logging.getLogger(__name__)

DOCUMENTATION_URL = "https://andrew-codechimp.github.io/HA-Battery-Notes/"

CONFIG_VERSION = 4

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SHOW_ALL_DEVICES): selector.BooleanSelector(),
        vol.Required(CONF_HIDE_BATTERY): selector.BooleanSelector(),
        vol.Required(CONF_ROUND_BATTERY): selector.BooleanSelector(),
        vol.Required(CONF_DEFAULT_BATTERY_LOW_THRESHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=99, mode=selector.NumberSelectorMode.BOX
            ),
        ),
        vol.Required(CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=99, mode=selector.NumberSelectorMode.BOX
            ),
        ),
        vol.Required(CONF_ADVANCED_SETTINGS): section(
            vol.Schema(
                {
                    vol.Required(CONF_ENABLE_AUTODISCOVERY): selector.BooleanSelector(),
                    vol.Required(CONF_ENABLE_REPLACED): selector.BooleanSelector(),
                    vol.Required(
                        CONF_HIDE_BATTERY_LOW, default=False
                    ): selector.BooleanSelector(),
                    vol.Optional(CONF_USER_LIBRARY): selector.TextSelector(),
                }
            ),
            {"collapsed": True},
        ),
    }
)

DEVICE_SCHEMA_ALL = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): selector.DeviceSelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT, autocomplete="off"
            ),
        ),
    }
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_ID): selector.DeviceSelector(
            config=selector.DeviceSelectorConfig(
                entity=[
                    selector.EntityFilterSelectorConfig(
                        domain=Platform.SENSOR,
                        device_class=SensorDeviceClass.BATTERY,
                    ),
                    selector.EntityFilterSelectorConfig(
                        domain=Platform.BINARY_SENSOR,
                        device_class=SensorDeviceClass.BATTERY,
                    ),
                ]
            )
        ),
        vol.Optional(CONF_NAME): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT, autocomplete="off"
            ),
        ),
    }
)

ENTITY_SCHEMA_ALL = vol.Schema(
    {
        vol.Required(CONF_SOURCE_ENTITY_ID): selector.EntitySelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT, autocomplete="off"
            ),
        ),
    }
)

ENTITY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SOURCE_ENTITY_ID): selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain=[Platform.SENSOR, Platform.BINARY_SENSOR],
                device_class=SensorDeviceClass.BATTERY,
            )
        ),
        vol.Optional(CONF_NAME): selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT, autocomplete="off"
            ),
        ),
    }
)


def none_if_empty(value: str | None) -> str | None:
    """Return None if the string is empty or None, otherwise return the string."""
    if value is None or value.strip() == "":
        return None
    return value


def calc_config_attributes(
    hass: HomeAssistant,
    data: dict,
) -> tuple[str, str]:
    """Calculate the unique ID and title for a battery notes configuration entry.

    This function determines the unique identifier and display title based on either
    a source entity ID or device ID. For entities, it combines device and entity names
    when available. For devices, it uses the device name directly.

    Args:
        hass: The Home Assistant instance.
        data: Configuration data dictionary containing either CONF_SOURCE_ENTITY_ID
              or CONF_DEVICE_ID, and optionally CONF_NAME.

    Returns:
        tuple[str, str]: A tuple containing:
            - unique_id (str): A unique identifier prefixed with "bn_" followed by
              either the entity's unique ID or device ID.
            - title (str): A human-readable title for the configuration entry. If CONF_NAME
              is provided, uses that value. Otherwise, constructs a title from device and/or
              entity names.

    """
    source_entity_id = data.get(CONF_SOURCE_ENTITY_ID)
    device_id = data.get(CONF_DEVICE_ID)

    entity_entry = None
    device_entry = None

    device_registry = dr.async_get(hass)

    if source_entity_id:
        entity_registry = er.async_get(hass)
        entity_entry = entity_registry.async_get(source_entity_id)
        _, source_object_id = split_entity_id(source_entity_id)
        if entity_entry:
            entity_unique_id = entity_entry.unique_id or entity_entry.entity_id
        else:
            entity_unique_id = source_object_id
        unique_id = f"bn_{entity_unique_id}"
    else:
        assert device_id
        unique_id = f"bn_{device_id}"

    if CONF_NAME in data:
        title = data.get(CONF_NAME)
    elif source_entity_id and entity_entry:
        if entity_entry.device_id:
            device_entry = device_registry.async_get(entity_entry.device_id)
            if device_entry:
                title = f"{device_entry.name_by_user or device_entry.name} - {entity_entry.name or entity_entry.original_name}"
            else:
                title = entity_entry.name or entity_entry.original_name
        else:
            title = entity_entry.name or entity_entry.original_name
    else:
        assert device_id
        device_entry = device_registry.async_get(device_id)
        assert device_entry
        title = device_entry.name_by_user or device_entry.name

    return (unique_id, str(title))


def _model_info(device_entry: dr.DeviceEntry | None) -> ModelInfo | None:
    """Return the library lookup details of a device, if it has enough."""
    if device_entry and device_entry.manufacturer and device_entry.model:
        return ModelInfo(
            device_entry.manufacturer,
            device_entry.model,
            get_device_model_id(device_entry),
            device_entry.hw_version,
        )
    return None


def _model_placeholders(model_info: ModelInfo | None) -> dict[str, str]:
    """Return the device details shown on the battery forms."""
    if model_info is None:
        return {"manufacturer": "", "model": "", "model_id": "", "hw_version": ""}
    return {
        "manufacturer": model_info.manufacturer,
        "model": model_info.model,
        "model_id": str(model_info.model_id or ""),
        "hw_version": str(model_info.hw_version or ""),
    }


async def _async_lookup_battery(
    hass: HomeAssistant, device_entry: dr.DeviceEntry | None
) -> tuple[ModelInfo | None, DeviceBatteryDetails | None]:
    """Update the library if due and look up the battery of a device."""
    library_updater = LibraryUpdater(hass)
    if await library_updater.time_to_update_library(1):
        await library_updater.get_library_updates()

    if (model_info := _model_info(device_entry)) is None:
        return None, None

    _LOGGER.debug("Looking up device %s", model_info)
    library = hass.data[DATA_LIBRARY]
    if not library.is_loaded:
        await library.load_libraries()

    device_battery_details = await library.get_device_battery_details(model_info)
    if device_battery_details and not device_battery_details.is_manual:
        _LOGGER.debug("Found device %s", model_info)
    return model_info, device_battery_details


def _apply_battery_details(
    data: dict[str, Any], device_battery_details: DeviceBatteryDetails | None
) -> None:
    """Suggest the library battery, defaulting to a single battery."""
    data[CONF_BATTERY_QUANTITY] = 1
    if device_battery_details and not device_battery_details.is_manual:
        data[CONF_BATTERY_TYPE] = device_battery_details.battery_type
        data[CONF_BATTERY_QUANTITY] = device_battery_details.battery_quantity


def _battery_schema(
    defaults: Mapping[str, Any] | None, include_name: bool = False
) -> vol.Schema:
    """Return the battery form, with defaults or for use with suggested values."""

    def key(
        marker: type[vol.Required | vol.Optional], name: str, *, default: Any
    ) -> vol.Marker:
        if defaults is None:
            return marker(name)
        return marker(name, default=default)

    number_box = selector.NumberSelectorMode.BOX
    text = selector.TextSelector(
        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
    )
    fields: dict[vol.Marker, Any] = {}
    if include_name:
        fields[vol.Optional(CONF_NAME)] = selector.TextSelector(
            selector.TextSelectorConfig(
                type=selector.TextSelectorType.TEXT, autocomplete="off"
            ),
        )
    data = defaults or {}
    fields.update(
        {
            key(
                vol.Required, CONF_BATTERY_TYPE, default=data.get(CONF_BATTERY_TYPE)
            ): text,
            key(
                vol.Required,
                CONF_BATTERY_QUANTITY,
                default=int(data.get(CONF_BATTERY_QUANTITY, 1)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=1, max=100, mode=number_box),
            ),
            key(vol.Optional, CONF_NOTE, default=data.get(CONF_NOTE, "")): text,
            key(
                vol.Required,
                CONF_BATTERY_LOW_THRESHOLD,
                default=int(data.get(CONF_BATTERY_LOW_THRESHOLD, 0)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=99, mode=number_box),
            ),
            key(
                vol.Required,
                CONF_BATTERY_INCREASE_THRESHOLD,
                default=int(data.get(CONF_BATTERY_INCREASE_THRESHOLD, 0)),
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(min=0, max=99, mode=number_box),
            ),
            vol.Required(CONF_ADVANCED_SETTINGS): section(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_BATTERY_PERCENTAGE_TEMPLATE
                        ): selector.TemplateSelector(),
                        vol.Optional(
                            CONF_BATTERY_LOW_TEMPLATE
                        ): selector.TemplateSelector(),
                        key(
                            vol.Optional, CONF_RETAIN_STATE, default=False
                        ): selector.BooleanSelector(),
                        key(
                            vol.Optional, CONF_FILTER_OUTLIERS, default=False
                        ): selector.BooleanSelector(),
                    }
                ),
                {"collapsed": True},
            ),
        }
    )
    return vol.Schema(fields)


def _apply_battery_input(data: dict[str, Any], user_input: dict[str, Any]) -> None:
    """Store the battery form input in the battery note data."""
    data[CONF_BATTERY_TYPE] = user_input[CONF_BATTERY_TYPE]
    data[CONF_BATTERY_QUANTITY] = int(user_input[CONF_BATTERY_QUANTITY])
    data[CONF_NOTE] = user_input.get(CONF_NOTE, "")
    data[CONF_BATTERY_LOW_THRESHOLD] = int(user_input[CONF_BATTERY_LOW_THRESHOLD])
    data[CONF_BATTERY_INCREASE_THRESHOLD] = int(
        user_input.get(CONF_BATTERY_INCREASE_THRESHOLD, 0)
    )
    advanced_input = user_input[CONF_ADVANCED_SETTINGS]
    advanced = data.setdefault(CONF_ADVANCED_SETTINGS, {})
    advanced[CONF_BATTERY_PERCENTAGE_TEMPLATE] = none_if_empty(
        advanced_input.get(CONF_BATTERY_PERCENTAGE_TEMPLATE)
    )
    advanced[CONF_BATTERY_LOW_TEMPLATE] = none_if_empty(
        advanced_input.get(CONF_BATTERY_LOW_TEMPLATE)
    )
    advanced[CONF_RETAIN_STATE] = advanced_input.get(CONF_RETAIN_STATE, False)
    advanced[CONF_FILTER_OUTLIERS] = advanced_input.get(CONF_FILTER_OUTLIERS, False)


class BatteryNotesFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for BatteryNotes."""

    VERSION = CONFIG_VERSION

    data: dict
    model_info: ModelInfo | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:  # noqa: ARG004
        # pylint: disable=unused-argument
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls,
        _: ConfigEntry,
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            SUBENTRY_BATTERY_NOTE: BatteryNotesSubentryFlowHandler,
        }

    async def async_get_integration_entry(self) -> ConfigEntry | None:
        """Return the main integration config entry, if it exists."""
        existing_entries = self.hass.config_entries.async_entries(
            domain=DOMAIN, include_ignore=False, include_disabled=False
        )
        # Only a single integration entry is allowed, don't rely on the title as users can rename it
        return existing_entries[0] if existing_entries else None

    async def async_step_integration_discovery(
        self,
        discovery_info: DiscoveryInfoType,
    ) -> ConfigFlowResult:
        """Handle integration discovery."""
        _LOGGER.debug("Starting discovery flow: %s", discovery_info)

        unique_id = f"bn_{discovery_info[CONF_DEVICE_ID]}"

        config_entry = await self.async_get_integration_entry()

        if not config_entry:
            return self.async_abort(reason="integration_not_added")

        for existing_subentry in config_entry.subentries.values():
            if existing_subentry.unique_id == unique_id:
                _LOGGER.debug("Subentry with unique_id %s already exists", unique_id)
                return self.async_abort(reason="already_configured")

        self.context["title_placeholders"] = {
            "name": f"{discovery_info[CONF_DEVICE_NAME]} - {discovery_info[CONF_INTEGRATION_NAME]}"
            if discovery_info[CONF_INTEGRATION_NAME]
            else discovery_info[CONF_DEVICE_NAME],
            "manufacturer": discovery_info[CONF_MANUFACTURER],
            "model": discovery_info[CONF_MODEL],
            "model_id": discovery_info[CONF_MODEL_ID],
            "hw_version": discovery_info[CONF_HW_VERSION],
        }

        await self.async_set_unique_id(unique_id)

        return await self.async_step_device(discovery_info)

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        # pylint: disable=unused-argument
        """Handle a flow initialized by the user."""

        if self._async_current_entries():
            _LOGGER.debug("An existing battery_notes config entry already exists")
            return self.async_abort(reason="already_configured")

        if user_input is not None:
            # Init defaults
            options = {
                CONF_SHOW_ALL_DEVICES: False,
                CONF_HIDE_BATTERY: False,
                CONF_ROUND_BATTERY: False,
                CONF_DEFAULT_BATTERY_LOW_THRESHOLD: DEFAULT_BATTERY_LOW_THRESHOLD,
                CONF_DEFAULT_BATTERY_INCREASE_THRESHOLD: DEFAULT_BATTERY_INCREASE_THRESHOLD,
                CONF_ADVANCED_SETTINGS: {
                    CONF_ENABLE_AUTODISCOVERY: True,
                    CONF_ENABLE_REPLACED: True,
                    CONF_HIDE_BATTERY_LOW: False,
                    CONF_USER_LIBRARY: "",
                },
            }

            return self.async_create_entry(
                title=INTEGRATION_NAME, data={}, options=options
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="user",
            description_placeholders={"documentation_url": DOCUMENTATION_URL},
        )

    async def async_step_device(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        """Handle a flow for a device or discovery."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data = user_input

            config_entry = await self.async_get_integration_entry()

            if not config_entry:
                return self.async_abort(reason="integration_not_added")

            device_entry = dr.async_get(self.hass).async_get(user_input[CONF_DEVICE_ID])
            self.model_info, device_battery_details = await _async_lookup_battery(
                self.hass, device_entry
            )
            _apply_battery_details(self.data, device_battery_details)

            return await self.async_step_battery()

        schema = DEVICE_SCHEMA
        # If show_all_devices = is specified and true, don't filter
        domain_config = self.hass.data.get(MY_KEY)
        if domain_config and domain_config.show_all_devices:
            schema = DEVICE_SCHEMA_ALL

        return self.async_show_form(
            step_id="device",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Second step in config flow to add the battery type."""
        errors: dict[str, str] = {}
        unique_id, title = calc_config_attributes(self.hass, self.data)

        if user_input is not None:
            config_entry = await self.async_get_integration_entry()

            if not config_entry:
                return self.async_abort(reason="integration_not_added")

            _apply_battery_input(self.data, user_input)

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Remove discovery data from data
            self.data.pop(CONF_DEVICE_NAME, None)
            self.data.pop(CONF_MANUFACTURER, None)
            self.data.pop(CONF_MODEL, None)
            self.data.pop(CONF_MODEL_ID, None)
            self.data.pop(CONF_HW_VERSION, None)
            self.data.pop(CONF_INTEGRATION_NAME, None)

            self.data.pop(CONF_NAME, None)

            subentry = ConfigSubentry(
                subentry_type=SUBENTRY_BATTERY_NOTE,
                data=MappingProxyType(self.data),
                title=title,
                unique_id=unique_id,
            )
            self.hass.config_entries.async_add_subentry(config_entry, subentry)

            return self.async_abort(reason="created_sub_entry")

        return self.async_show_form(
            step_id="battery",
            description_placeholders={
                "name": title,
                **_model_placeholders(self.model_info),
            },
            data_schema=_battery_schema(self.data),
            errors=errors,
        )


class OptionsFlowHandler(OptionsFlow):
    """Options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""

        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA,
                self.config_entry.options,
            ),
        )


class BatteryNotesSubentryFlowHandler(ConfigSubentryFlow):
    """Flow for managing Battery Notes subentries."""

    data: dict[str, Any]
    model_info: ModelInfo | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> SubentryFlowResult:
        """Add a subentry."""

        return self.async_show_menu(
            step_id="user",
            menu_options=["device", "entity"],
            description_placeholders={"documentation_url": DOCUMENTATION_URL},
        )

    async def async_step_device(
        self,
        user_input: dict | None = None,
    ) -> SubentryFlowResult:
        """Handle a flow for a device or discovery."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data = user_input

            device_entry = dr.async_get(self.hass).async_get(user_input[CONF_DEVICE_ID])
            self.model_info, device_battery_details = await _async_lookup_battery(
                self.hass, device_entry
            )
            _apply_battery_details(self.data, device_battery_details)

            if device_battery_details and device_battery_details.is_manual:
                return await self.async_step_manual()

            return await self.async_step_battery()

        schema = DEVICE_SCHEMA
        # If show_all_devices = is specified and true, don't filter
        domain_config = self.hass.data.get(MY_KEY)
        if domain_config and domain_config.show_all_devices:
            schema = DEVICE_SCHEMA_ALL

        return self.async_show_form(
            step_id="device",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )

    async def async_step_entity(
        self,
        user_input: dict | None = None,
    ) -> SubentryFlowResult:
        """Handle a flow for a device or discovery."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data = user_input

            source_entity_id = user_input[CONF_SOURCE_ENTITY_ID]
            self.data[CONF_SOURCE_ENTITY_ID] = source_entity_id
            entity_entry = er.async_get(self.hass).async_get(source_entity_id)

            if entity_entry:
                device_battery_details = None
                if entity_entry.device_id:
                    self.data[CONF_DEVICE_ID] = entity_entry.device_id
                    device_entry = dr.async_get(self.hass).async_get(
                        entity_entry.device_id
                    )
                    (
                        self.model_info,
                        device_battery_details,
                    ) = await _async_lookup_battery(self.hass, device_entry)
                _apply_battery_details(self.data, device_battery_details)

                if device_battery_details and device_battery_details.is_manual:
                    return await self.async_step_manual()
                return await self.async_step_battery()

            # No entity_registry entry, must be a config.yaml entity which we can't support
            errors["base"] = "unconfigurable_entity"

        schema = ENTITY_SCHEMA_ALL

        return self.async_show_form(
            step_id="entity",
            data_schema=schema,
            errors=errors,
            last_step=False,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Second step in config flow to add the battery type."""
        # pylint: disable=unused-argument
        errors: dict[str, str] = {}
        if user_input is not None:
            return await self.async_step_battery()

        return self.async_show_form(
            step_id="manual",
            data_schema=None,
            last_step=False,
            errors=errors,
        )

    async def async_step_battery(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Second step in config flow to add the battery type."""
        errors: dict[str, str] = {}
        unique_id, title = calc_config_attributes(self.hass, self.data)

        if user_input is not None:
            _apply_battery_input(self.data, user_input)

            # Check if unique_id already exists
            config_entry = self._get_entry()
            for existing_subentry in config_entry.subentries.values():
                if existing_subentry.unique_id == unique_id:
                    _LOGGER.debug(
                        "Subentry with unique_id %s already exists", unique_id
                    )
                    return self.async_abort(reason="already_configured")

            self.data.pop(CONF_NAME, None)

            return self.async_create_entry(
                title=title, data=self.data, unique_id=unique_id
            )

        return self.async_show_form(
            step_id="battery",
            description_placeholders={
                "name": title,
                **_model_placeholders(self.model_info),
            },
            data_schema=_battery_schema(self.data),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to modify an existing battery note."""
        errors: dict[str, str] = {}

        if user_input is not None:
            _apply_battery_input(self.data, user_input)

            # Save the updated subentry, the name is held in the title not the data
            self.data.pop(CONF_NAME, None)
            new_title = user_input.pop(
                CONF_NAME, self._get_reconfigure_subentry().title
            )

            return self.async_update_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                title=new_title,
                data=self.data,
            )

        config_subentry = self._get_reconfigure_subentry()
        self.data = copy.deepcopy(dict(config_subentry.data))
        self.data.setdefault(CONF_ADVANCED_SETTINGS, {})

        if source_device_id := self.data.get(CONF_DEVICE_ID):
            device_entry = dr.async_get(self.hass).async_get(source_device_id)
            if not device_entry:
                errors["base"] = "orphaned_battery_note"
            self.model_info = _model_info(device_entry)

        self.data[CONF_NAME] = config_subentry.title
        return self.async_show_form(
            step_id="reconfigure",
            description_placeholders=_model_placeholders(self.model_info),
            data_schema=self.add_suggested_values_to_schema(
                _battery_schema(None, include_name=True), self.data
            ),
            errors=errors,
        )

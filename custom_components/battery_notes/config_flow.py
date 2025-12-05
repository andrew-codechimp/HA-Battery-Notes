"""Adds config flow for BatteryNotes."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

import voluptuous as vol

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
from homeassistant import config_entries
from homeassistant.core import callback, split_entity_id
from homeassistant.const import CONF_NAME, CONF_DEVICE_ID, Platform
from homeassistant.helpers import selector
from homeassistant.config_entries import (
    ConfigEntry,
    OptionsFlow,
    ConfigSubentry,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.helpers.typing import DiscoveryInfoType
from homeassistant.data_entry_flow import section
from homeassistant.components.sensor.const import SensorDeviceClass

from .const import (
    NAME as INTEGRATION_NAME,
    DOMAIN,
    CONF_MODEL,
    CONF_MODEL_ID,
    CONF_HW_VERSION,
    CONF_DEVICE_NAME,
    CONF_BATTERY_TYPE,
    CONF_HIDE_BATTERY,
    CONF_MANUFACTURER,
    CONF_USER_LIBRARY,
    CONF_ROUND_BATTERY,
    CONF_ENABLE_REPLACED,
    CONF_FILTER_OUTLIERS,
    CONF_BATTERY_QUANTITY,
    CONF_INTEGRATION_NAME,
    CONF_SHOW_ALL_DEVICES,
    CONF_SOURCE_ENTITY_ID,
    SUBENTRY_BATTERY_NOTE,
    CONF_ADVANCED_SETTINGS,
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_ENABLE_AUTODISCOVERY,
    CONF_BATTERY_LOW_THRESHOLD,
    DEFAULT_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_INCREASE_THRESHOLD,
    CONF_DEFAULT_BATTERY_LOW_THRESHOLD,
    DEFAULT_BATTERY_INCREASE_THRESHOLD,
)
from .common import get_device_model_id
from .library import DATA_LIBRARY, ModelInfo
from .coordinator import MY_KEY
from .library_updater import LibraryUpdater

_LOGGER = logging.getLogger(__name__)

DOCUMENTATION_URL = "https://andrew-codechimp.github.io/HA-Battery-Notes/"

CONFIG_VERSION = 3

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
        vol.Required(CONF_BATTERY_INCREASE_THRESHOLD): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0, max=99, mode=selector.NumberSelectorMode.BOX
            ),
        ),
        vol.Required(CONF_ADVANCED_SETTINGS): section(
            vol.Schema(
                {
                    vol.Required(CONF_ENABLE_AUTODISCOVERY): selector.BooleanSelector(),
                    vol.Required(CONF_ENABLE_REPLACED): selector.BooleanSelector(),
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
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
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
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
        ),
    }
)

ENTITY_SCHEMA_ALL = vol.Schema(
    {
        vol.Required(CONF_SOURCE_ENTITY_ID): selector.EntitySelector(),
        vol.Optional(CONF_NAME): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
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
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
        ),
    }
)


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
        config_entry: ConfigEntry,  # noqa: ARG003
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
        for entry in existing_entries:
            if entry.title == INTEGRATION_NAME:
                return entry
        return None

    async def async_step_integration_discovery(
        self,
        discovery_info: DiscoveryInfoType,
    ) -> ConfigFlowResult:
        """Handle integration discovery."""
        _LOGGER.debug("Starting discovery flow: %s", discovery_info)

        unique_id = f"bn_{discovery_info[CONF_DEVICE_ID]}"

        config_entry = await self.async_get_integration_entry()

        if not config_entry:
            _LOGGER.debug("No existing single config entry found, creating new one")

            # Init defaults
            options = {
                CONF_SHOW_ALL_DEVICES: False,
                CONF_HIDE_BATTERY: False,
                CONF_ROUND_BATTERY: False,
                CONF_DEFAULT_BATTERY_LOW_THRESHOLD: DEFAULT_BATTERY_LOW_THRESHOLD,
                CONF_BATTERY_INCREASE_THRESHOLD: DEFAULT_BATTERY_INCREASE_THRESHOLD,
                CONF_ADVANCED_SETTINGS: {
                    CONF_ENABLE_AUTODISCOVERY: True,
                    CONF_ENABLE_REPLACED: True,
                    CONF_USER_LIBRARY: "",
                },
            }

            self.async_create_entry(title=INTEGRATION_NAME, data={}, options=options)
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
                CONF_BATTERY_INCREASE_THRESHOLD: DEFAULT_BATTERY_INCREASE_THRESHOLD,
                CONF_ADVANCED_SETTINGS: {
                    CONF_ENABLE_AUTODISCOVERY: True,
                    CONF_ENABLE_REPLACED: True,
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
        device_battery_details = None

        if user_input is not None:
            self.data = user_input

            config_entry = await self.async_get_integration_entry()

            if not config_entry:
                return self.async_abort(reason="integration_not_added")

            device_id = user_input[CONF_DEVICE_ID]

            library_updater = LibraryUpdater(self.hass)
            if await library_updater.time_to_update_library(1):
                await library_updater.get_library_updates()

            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get(device_id)

            if device_entry and device_entry.manufacturer and device_entry.model:
                _LOGGER.debug(
                    "Looking up device %s %s %s %s",
                    device_entry.manufacturer,
                    device_entry.model,
                    get_device_model_id(device_entry) or "",
                    device_entry.hw_version,
                )

                self.model_info = ModelInfo(
                    device_entry.manufacturer,
                    device_entry.model,
                    get_device_model_id(device_entry),
                    device_entry.hw_version,
                )

                library = self.hass.data[DATA_LIBRARY]
                if not library.is_loaded:
                    await library.load_libraries()

                # Set defaults if not found in library
                self.data[CONF_BATTERY_QUANTITY] = 1

                device_battery_details = await library.get_device_battery_details(
                    self.model_info
                )

                if device_battery_details and not device_battery_details.is_manual:
                    _LOGGER.debug(
                        "Found device %s %s %s %s",
                        device_entry.manufacturer,
                        device_entry.model,
                        get_device_model_id(device_entry) or "",
                        device_entry.hw_version,
                    )
                    self.data[CONF_BATTERY_TYPE] = device_battery_details.battery_type

                    self.data[CONF_BATTERY_QUANTITY] = (
                        device_battery_details.battery_quantity
                    )

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

    async def async_step_battery(  # noqa: PLR0912, PLR0915
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Second step in config flow to add the battery type."""
        errors: dict[str, str] = {}
        if user_input is not None:
            config_entry = await self.async_get_integration_entry()

            if not config_entry:
                return self.async_abort(reason="integration_not_added")

            self.data[CONF_BATTERY_TYPE] = user_input[CONF_BATTERY_TYPE]
            self.data[CONF_BATTERY_QUANTITY] = int(user_input[CONF_BATTERY_QUANTITY])
            self.data[CONF_BATTERY_LOW_THRESHOLD] = int(
                user_input[CONF_BATTERY_LOW_THRESHOLD]
            )
            self.data[CONF_BATTERY_LOW_TEMPLATE] = user_input.get(
                CONF_BATTERY_LOW_TEMPLATE, None
            )
            self.data[CONF_FILTER_OUTLIERS] = user_input.get(
                CONF_FILTER_OUTLIERS, False
            )

            source_entity_id = self.data.get(CONF_SOURCE_ENTITY_ID, None)
            device_id = self.data.get(CONF_DEVICE_ID, None)

            entity_entry = None
            device_entry = None

            if source_entity_id:
                entity_registry = er.async_get(self.hass)
                entity_entry = entity_registry.async_get(source_entity_id)
                _, source_object_id = split_entity_id(source_entity_id)
                if entity_entry:
                    entity_unique_id = entity_entry.unique_id or entity_entry.entity_id
                else:
                    entity_unique_id = source_object_id
                unique_id = f"bn_{entity_unique_id}"
            else:
                device_registry = dr.async_get(self.hass)
                assert device_id
                device_entry = device_registry.async_get(device_id)
                unique_id = f"bn_{device_id}"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            if CONF_NAME in self.data:
                title = self.data.pop(CONF_NAME)
            elif source_entity_id and entity_entry:
                if entity_entry.device_id:
                    device_registry = dr.async_get(self.hass)
                    device_entry = device_registry.async_get(entity_entry.device_id)
                    if device_entry:
                        title = f"{device_entry.name_by_user or device_entry.name} - {entity_entry.name or entity_entry.original_name}"
                    else:
                        title = entity_entry.name or entity_entry.original_name
                else:
                    title = entity_entry.name or entity_entry.original_name
            else:
                assert device_entry
                title = device_entry.name_by_user or device_entry.name

            # Remove discovery data from data
            self.data.pop(CONF_DEVICE_NAME, None)
            self.data.pop(CONF_MANUFACTURER, None)
            self.data.pop(CONF_MODEL, None)
            self.data.pop(CONF_MODEL_ID, None)
            self.data.pop(CONF_HW_VERSION, None)
            self.data.pop(CONF_INTEGRATION_NAME, None)

            subentry = ConfigSubentry(
                subentry_type=SUBENTRY_BATTERY_NOTE,
                data=MappingProxyType(self.data),
                title=str(title),
                unique_id=unique_id,
            )
            self.hass.config_entries.async_add_subentry(config_entry, subentry)

            return self.async_abort(reason="created_sub_entry")

        return self.async_show_form(
            step_id="battery",
            description_placeholders={
                "manufacturer": self.model_info.manufacturer if self.model_info else "",
                "model": self.model_info.model if self.model_info else "",
                "model_id": (
                    str(self.model_info.model_id or "") if self.model_info else ""
                ),
                "hw_version": (
                    str(self.model_info.hw_version or "") if self.model_info else ""
                ),
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BATTERY_TYPE,
                        default=self.data.get(CONF_BATTERY_TYPE),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_QUANTITY,
                        default=int(self.data.get(CONF_BATTERY_QUANTITY, 1)),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=100, mode=selector.NumberSelectorMode.BOX
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_LOW_THRESHOLD,
                        default=int(self.data.get(CONF_BATTERY_LOW_THRESHOLD, 0)),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=99, mode=selector.NumberSelectorMode.BOX
                        ),
                    ),
                    vol.Optional(
                        CONF_BATTERY_LOW_TEMPLATE
                    ): selector.TemplateSelector(),
                    vol.Optional(
                        CONF_FILTER_OUTLIERS, default=False
                    ): selector.BooleanSelector(),
                }
            ),
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

    @property
    def _is_new(self) -> bool:
        """Return if this is a new subentry."""
        return self.source == "user"

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
        device_battery_details = None

        if user_input is not None:
            self.data = user_input

            device_id = user_input[CONF_DEVICE_ID]

            library_updater = LibraryUpdater(self.hass)
            if await library_updater.time_to_update_library(1):
                await library_updater.get_library_updates()

            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get(device_id)

            if device_entry and device_entry.manufacturer and device_entry.model:
                _LOGGER.debug(
                    "Looking up device %s %s %s %s",
                    device_entry.manufacturer,
                    device_entry.model,
                    get_device_model_id(device_entry) or "",
                    device_entry.hw_version,
                )

                self.model_info = ModelInfo(
                    device_entry.manufacturer,
                    device_entry.model,
                    get_device_model_id(device_entry),
                    device_entry.hw_version,
                )

                library = self.hass.data[DATA_LIBRARY]
                if not library.is_loaded:
                    await library.load_libraries()

                # Set defaults if not found in library
                self.data[CONF_BATTERY_QUANTITY] = 1

                device_battery_details = await library.get_device_battery_details(
                    self.model_info
                )

                if device_battery_details and not device_battery_details.is_manual:
                    _LOGGER.debug(
                        "Found device %s %s %s %s",
                        device_entry.manufacturer,
                        device_entry.model,
                        get_device_model_id(device_entry) or "",
                        device_entry.hw_version,
                    )
                    self.data[CONF_BATTERY_TYPE] = device_battery_details.battery_type

                    self.data[CONF_BATTERY_QUANTITY] = (
                        device_battery_details.battery_quantity
                    )

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
        device_battery_details = None

        if user_input is not None:
            self.data = user_input

            source_entity_id = user_input[CONF_SOURCE_ENTITY_ID]
            self.data[CONF_SOURCE_ENTITY_ID] = source_entity_id
            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.async_get(source_entity_id)

            # Default battery quantity if not found in library lookup
            self.data[CONF_BATTERY_QUANTITY] = 1

            if entity_entry:
                if entity_entry.device_id:
                    self.data[CONF_DEVICE_ID] = entity_entry.device_id

                    library_updater = LibraryUpdater(self.hass)
                    if await library_updater.time_to_update_library(1):
                        await library_updater.get_library_updates()

                    device_registry = dr.async_get(self.hass)
                    device_entry = device_registry.async_get(entity_entry.device_id)

                    if (
                        device_entry
                        and device_entry.manufacturer
                        and device_entry.model
                    ):
                        _LOGGER.debug(
                            "Looking up device %s %s %s %s",
                            device_entry.manufacturer,
                            device_entry.model,
                            get_device_model_id(device_entry) or "",
                            device_entry.hw_version,
                        )

                        self.model_info = ModelInfo(
                            device_entry.manufacturer,
                            device_entry.model,
                            get_device_model_id(device_entry),
                            device_entry.hw_version,
                        )

                        library = self.hass.data[DATA_LIBRARY]
                        if not library.is_loaded:
                            await library.load_libraries()

                        device_battery_details = (
                            await library.get_device_battery_details(self.model_info)
                        )

                        if (
                            device_battery_details
                            and not device_battery_details.is_manual
                        ):
                            _LOGGER.debug(
                                "Found device %s %s %s %s",
                                device_entry.manufacturer,
                                device_entry.model,
                                get_device_model_id(device_entry) or "",
                                device_entry.hw_version,
                            )
                            self.data[CONF_BATTERY_TYPE] = (
                                device_battery_details.battery_type
                            )

                            self.data[CONF_BATTERY_QUANTITY] = (
                                device_battery_details.battery_quantity
                            )

                        if device_battery_details and device_battery_details.is_manual:
                            return await self.async_step_manual()
                return await self.async_step_battery()
            else:
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

    async def async_step_battery(  # noqa: PLR0912
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Second step in config flow to add the battery type."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data[CONF_BATTERY_TYPE] = user_input[CONF_BATTERY_TYPE]
            self.data[CONF_BATTERY_QUANTITY] = int(user_input[CONF_BATTERY_QUANTITY])
            self.data[CONF_BATTERY_LOW_THRESHOLD] = int(
                user_input[CONF_BATTERY_LOW_THRESHOLD]
            )
            self.data[CONF_BATTERY_LOW_TEMPLATE] = user_input.get(
                CONF_BATTERY_LOW_TEMPLATE, None
            )
            self.data[CONF_FILTER_OUTLIERS] = user_input.get(
                CONF_FILTER_OUTLIERS, False
            )

            source_entity_id = self.data.get(CONF_SOURCE_ENTITY_ID, None)
            device_id = self.data.get(CONF_DEVICE_ID, None)

            entity_entry = None
            device_entry = None

            if source_entity_id:
                entity_registry = er.async_get(self.hass)
                entity_entry = entity_registry.async_get(source_entity_id)
                _, source_object_id = split_entity_id(source_entity_id)
                if entity_entry:
                    entity_unique_id = entity_entry.unique_id or entity_entry.entity_id
                else:
                    entity_unique_id = source_object_id
                unique_id = f"bn_{entity_unique_id}"
            else:
                device_registry = dr.async_get(self.hass)
                assert device_id
                device_entry = device_registry.async_get(device_id)
                unique_id = f"bn_{device_id}"

            # Check if unique_id already exists
            config_entry = self._get_entry()
            for existing_subentry in config_entry.subentries.values():
                if existing_subentry.unique_id == unique_id:
                    _LOGGER.debug(
                        "Subentry with unique_id %s already exists", unique_id
                    )
                    return self.async_abort(reason="already_configured")

            if CONF_NAME in self.data:
                title = self.data.pop(CONF_NAME)
            elif source_entity_id and entity_entry:
                if entity_entry.device_id:
                    device_registry = dr.async_get(self.hass)
                    device_entry = device_registry.async_get(entity_entry.device_id)
                    if device_entry:
                        title = f"{device_entry.name_by_user or device_entry.name} - {entity_entry.name or entity_entry.original_name}"
                    else:
                        title = entity_entry.name or entity_entry.original_name
                else:
                    title = entity_entry.name or entity_entry.original_name
            else:
                assert device_entry
                title = device_entry.name_by_user or device_entry.name

            return self.async_create_entry(
                title=str(title), data=self.data, unique_id=unique_id
            )

        return self.async_show_form(
            step_id="battery",
            description_placeholders={
                "manufacturer": self.model_info.manufacturer if self.model_info else "",
                "model": self.model_info.model if self.model_info else "",
                "model_id": (
                    str(self.model_info.model_id or "") if self.model_info else ""
                ),
                "hw_version": (
                    str(self.model_info.hw_version or "") if self.model_info else ""
                ),
            },
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_BATTERY_TYPE,
                        default=self.data.get(CONF_BATTERY_TYPE),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_QUANTITY,
                        default=int(self.data.get(CONF_BATTERY_QUANTITY, 1)),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=100, mode=selector.NumberSelectorMode.BOX
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_LOW_THRESHOLD,
                        default=int(self.data.get(CONF_BATTERY_LOW_THRESHOLD, 0)),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=99, mode=selector.NumberSelectorMode.BOX
                        ),
                    ),
                    vol.Optional(
                        CONF_BATTERY_LOW_TEMPLATE
                    ): selector.TemplateSelector(),
                    vol.Optional(
                        CONF_FILTER_OUTLIERS, default=False
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to modify an existing battery note."""
        errors: dict[str, str] = {}

        config_subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            self.data[CONF_BATTERY_TYPE] = user_input[CONF_BATTERY_TYPE]
            self.data[CONF_BATTERY_QUANTITY] = int(user_input[CONF_BATTERY_QUANTITY])
            self.data[CONF_BATTERY_LOW_THRESHOLD] = int(
                user_input[CONF_BATTERY_LOW_THRESHOLD]
            )
            if user_input.get(CONF_BATTERY_LOW_TEMPLATE, "") == "":
                self.data[CONF_BATTERY_LOW_TEMPLATE] = None
            else:
                self.data[CONF_BATTERY_LOW_TEMPLATE] = user_input[
                    CONF_BATTERY_LOW_TEMPLATE
                ]
            self.data[CONF_FILTER_OUTLIERS] = user_input.get(
                CONF_FILTER_OUTLIERS, False
            )

            # Save the updated subentry
            new_title = user_input.pop(CONF_NAME)

            return self.async_update_and_abort(
                self._get_entry(),
                self._get_reconfigure_subentry(),
                title=new_title,
                data=self.data,
            )

        self.data = config_subentry.data.copy()

        source_device_id = self.data.get(CONF_DEVICE_ID)

        if source_device_id:
            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get(source_device_id)

            if not device_entry:
                errors["base"] = "orphaned_battery_note"
            elif device_entry and device_entry.manufacturer and device_entry.model:
                _LOGGER.debug(
                    "Looking up device %s %s %s %s",
                    device_entry.manufacturer,
                    device_entry.model,
                    get_device_model_id(device_entry) or "",
                    device_entry.hw_version,
                )

                self.model_info = ModelInfo(
                    device_entry.manufacturer,
                    device_entry.model,
                    get_device_model_id(device_entry),
                    device_entry.hw_version,
                )

        if self.data.get(CONF_BATTERY_LOW_TEMPLATE, None) is None:
            data_schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_NAME, default=config_subentry.title
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_TYPE, default=self.data[CONF_BATTERY_TYPE]
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_QUANTITY, default=self.data[CONF_BATTERY_QUANTITY]
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=100, mode=selector.NumberSelectorMode.BOX
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_LOW_THRESHOLD,
                        default=self.data.get(CONF_BATTERY_LOW_THRESHOLD, 0),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=99, mode=selector.NumberSelectorMode.BOX
                        ),
                    ),
                    vol.Optional(
                        CONF_BATTERY_LOW_TEMPLATE
                    ): selector.TemplateSelector(),
                    vol.Optional(
                        CONF_FILTER_OUTLIERS,
                        default=self.data.get(CONF_FILTER_OUTLIERS, False),
                    ): selector.BooleanSelector(),
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_NAME, default=config_subentry.title
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_TYPE, default=self.data[CONF_BATTERY_TYPE]
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_QUANTITY, default=self.data[CONF_BATTERY_QUANTITY]
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1, max=100, mode=selector.NumberSelectorMode.BOX
                        ),
                    ),
                    vol.Required(
                        CONF_BATTERY_LOW_THRESHOLD,
                        default=self.data.get(CONF_BATTERY_LOW_THRESHOLD, 0),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=99, mode=selector.NumberSelectorMode.BOX
                        ),
                    ),
                    vol.Optional(
                        CONF_BATTERY_LOW_TEMPLATE,
                        default=self.data.get(CONF_BATTERY_LOW_TEMPLATE, None),
                    ): selector.TemplateSelector(),
                    vol.Optional(
                        CONF_FILTER_OUTLIERS,
                        default=self.data.get(CONF_FILTER_OUTLIERS, False),
                    ): selector.BooleanSelector(),
                }
            )

        return self.async_show_form(
            step_id="reconfigure",
            description_placeholders={
                "manufacturer": self.model_info.manufacturer if self.model_info else "",
                "model": self.model_info.model if self.model_info else "",
                "model_id": (
                    str(self.model_info.model_id or "") if self.model_info else ""
                ),
                "hw_version": (
                    str(self.model_info.hw_version or "") if self.model_info else ""
                ),
            },
            data_schema=data_schema,
            errors=errors,
        )

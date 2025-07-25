"""Adds config flow for BatteryNotes."""

from __future__ import annotations

import copy
import logging
from typing import Any

import homeassistant.helpers.device_registry as dr
import homeassistant.helpers.entity_registry as er
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.sensor.const import SensorDeviceClass
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    Platform,
)
from homeassistant.core import callback, split_entity_id
from homeassistant.helpers import selector
from homeassistant.helpers.typing import DiscoveryInfoType

from .common import get_device_model_id
from .const import (
    CONF_BATTERY_LOW_TEMPLATE,
    CONF_BATTERY_LOW_THRESHOLD,
    CONF_BATTERY_QUANTITY,
    CONF_BATTERY_TYPE,
    CONF_DEVICE_NAME,
    CONF_FILTER_OUTLIERS,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_MODEL_ID,
    CONF_SOURCE_ENTITY_ID,
    DOMAIN,
)
from .coordinator import MY_KEY
from .library import Library, ModelInfo
from .library_updater import LibraryUpdater

_LOGGER = logging.getLogger(__name__)

CONFIG_VERSION = 2

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
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        # pylint: disable=unused-argument
        """Get the options flow for this handler."""
        return OptionsFlowHandler()

    async def async_step_integration_discovery(
        self,
        discovery_info: DiscoveryInfoType,
    ) -> ConfigFlowResult:
        """Handle integration discovery."""
        _LOGGER.debug("Starting discovery flow: %s", discovery_info)

        unique_id = f"bn_{discovery_info[CONF_DEVICE_ID]}"
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {
            "name": discovery_info[CONF_DEVICE_NAME],
            "manufacturer": discovery_info[CONF_MANUFACTURER],
            "model": discovery_info[CONF_MODEL],
            "model_id": discovery_info[CONF_MODEL_ID],
        }

        return await self.async_step_device(discovery_info)

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
        # pylint: disable=unused-argument
        """Handle a flow initialized by the user."""

        return self.async_show_menu(step_id="user", menu_options=["device", "entity"])

    async def async_step_device(
        self,
        user_input: dict | None = None,
    ) -> ConfigFlowResult:
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

                library = Library(self.hass)
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
    ) -> ConfigFlowResult:
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

                        library = Library(self.hass)
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

    async def async_step_manual(self, user_input: dict[str, Any] | None = None):
        """Second step in config flow to add the battery type."""
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
    ) -> ConfigFlowResult:
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
            self.data[CONF_FILTER_OUTLIERS] = user_input.get(CONF_FILTER_OUTLIERS, False)

            source_entity_id = self.data.get(CONF_SOURCE_ENTITY_ID, None)
            device_id = self.data.get(CONF_DEVICE_ID, None)

            entity_entry = None
            device_entry = None

            if source_entity_id:
                entity_registry = er.async_get(self.hass)
                entity_entry = entity_registry.async_get(source_entity_id)
                source_entity_domain, source_object_id = split_entity_id(
                    source_entity_id
                )
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
                title = self.data.get(CONF_NAME)
            elif source_entity_id and entity_entry:
                title = entity_entry.name or entity_entry.original_name
            else:
                assert device_entry
                title = device_entry.name_by_user or device_entry.name

            return self.async_create_entry(
                title=str(title),
                data=self.data,
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
                        CONF_FILTER_OUTLIERS,
                        default=False): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )


class OptionsFlowHandler(OptionsFlow):
    """Handle an option flow for BatteryNotes."""

    model_info: ModelInfo | None = None

    def __init__(self) -> None:
        """Initialize options flow."""
        self.current_config: dict
        self.source_device_id: str
        self.name: str
        self.battery_type: str
        self.battery_quantity: int
        self.battery_low_template: str
        self.filter_outliers: bool

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle options flow."""
        errors = {}
        self.current_config = dict(self.config_entry.data)
        self.source_device_id = self.current_config.get(CONF_DEVICE_ID)  # type: ignore
        self.name = str(self.current_config.get(CONF_NAME) or "")
        self.battery_type = str(self.current_config.get(CONF_BATTERY_TYPE) or "")
        self.battery_quantity = int(self.current_config.get(CONF_BATTERY_QUANTITY) or 1)
        self.battery_low_template = str(
            self.current_config.get(CONF_BATTERY_LOW_TEMPLATE) or ""
        )
        self.filter_outliers = bool(
            self.current_config.get(CONF_FILTER_OUTLIERS) or False
        )

        if self.source_device_id:
            device_registry = dr.async_get(self.hass)
            device_entry = device_registry.async_get(self.source_device_id)

            if not device_entry:
                errors["base"] = "orphaned_battery_note"
            else:
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

        schema = self.build_options_schema()
        if user_input is not None:
            user_input[CONF_BATTERY_QUANTITY] = int(user_input[CONF_BATTERY_QUANTITY])
            user_input[CONF_BATTERY_LOW_THRESHOLD] = int(
                user_input[CONF_BATTERY_LOW_THRESHOLD]
            )
            # user_input[CONF_BATTERY_LOW_TEMPLATE] = user_input.get(CONF_BATTERY_LOW_TEMPLATE, None)
            errors = await self.save_options(user_input, schema)
            if not errors:
                return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="init",
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
            data_schema=schema,
            errors=errors,
        )

    async def save_options(
        self,
        user_input: dict[str, Any],
        schema: vol.Schema,
    ) -> dict:
        """Save options, and return errors when validation fails."""
        errors = {}

        device_registry = dr.async_get(self.hass)
        device_entry = device_registry.async_get(
            str(self.config_entry.data.get(CONF_DEVICE_ID))
        )

        source_entity_id = self.config_entry.data.get(CONF_SOURCE_ENTITY_ID, None)

        entity_entry: er.RegistryEntry | None = None
        if source_entity_id:
            entity_registry = er.async_get(self.hass)
            entity_entry = entity_registry.async_get(source_entity_id)
            if not entity_entry:
                errors["base"] = "orphaned_battery_note"
                return errors
        else:
            if not device_entry:
                errors["base"] = "orphaned_battery_note"
                return errors

        title: Any = ""
        if CONF_NAME in user_input:
            title = user_input.get(CONF_NAME)
        elif source_entity_id and entity_entry:
            title = entity_entry.name or entity_entry.original_name
        elif device_entry:
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
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_NAME): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                ),
                vol.Required(CONF_BATTERY_TYPE): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                ),
                vol.Required(CONF_BATTERY_QUANTITY): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=100, mode=selector.NumberSelectorMode.BOX
                    ),
                ),
                vol.Required(CONF_BATTERY_LOW_THRESHOLD): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=99, mode=selector.NumberSelectorMode.BOX
                    ),
                ),
                vol.Optional(CONF_BATTERY_LOW_TEMPLATE): selector.TemplateSelector(),
                vol.Optional(CONF_FILTER_OUTLIERS): selector.BooleanSelector(),
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

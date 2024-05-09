"""Binary Sensor platform for battery_notes."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import (
    HomeAssistant,
    callback,
    Event,
    split_entity_id,
)
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.start import async_at_start
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.event import (
    EventStateChangedData,
    TrackTemplate,
    TrackTemplateResult,
    async_track_template_result,
)

from homeassistant.helpers import template
from homeassistant.helpers.template import (
    Template,
    TemplateStateFromEntityId,
)
from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA,
    BinarySensorEntity,
    BinarySensorEntityDescription,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
)
from homeassistant.helpers.reload import async_setup_reload_service

from homeassistant.const import (
    CONF_NAME,
    CONF_DEVICE_ID,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from . import PLATFORMS

from .const import (
    DOMAIN,
    DATA,
    ATTR_BATTERY_LOW_THRESHOLD,
    CONF_SOURCE_ENTITY_ID,
)

from .common import validate_is_float

from .device import BatteryNotesDevice
from .coordinator import BatteryNotesCoordinator

from .entity import (
    BatteryNotesEntityDescription,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class BatteryNotesBinarySensorEntityDescription(
    BatteryNotesEntityDescription,
    BinarySensorEntityDescription,
):
    """Describes Battery Notes button entity."""

    unique_id_suffix: str

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_DEVICE_ID): cv.string,
        vol.Optional(CONF_SOURCE_ENTITY_ID): cv.string,
    }
)

@callback
def async_add_to_device(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Add our config entry to the device."""
    device_registry = dr.async_get(hass)

    device_id = entry.data.get(CONF_DEVICE_ID)

    if device_id:
        if device_registry.async_get(device_id):
            device_registry.async_update_device(device_id, add_config_entry_id=entry.entry_id)
            return device_id
    return None

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Battery Type config entry."""
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    device_id = config_entry.data.get(CONF_DEVICE_ID)

    async def async_registry_updated(event: Event) -> None:
        """Handle entity registry update."""
        data = event.data
        if data["action"] == "remove":
            await hass.config_entries.async_remove(config_entry.entry_id)

        if data["action"] != "update":
            return

        if "entity_id" in data["changes"]:
            # Entity_id changed, reload the config entry
            await hass.config_entries.async_reload(config_entry.entry_id)

        if device_id and "device_id" in data["changes"]:
            # If the tracked battery note is no longer in the device, remove our config entry
            # from the device
            if (
                not (entity_entry := entity_registry.async_get(data["entity_id"]))
                or not device_registry.async_get(device_id)
                or entity_entry.device_id == device_id
            ):
                # No need to do any cleanup
                return

            device_registry.async_update_device(
                device_id, remove_config_entry_id=config_entry.entry_id
            )

    coordinator: BatteryNotesCoordinator = hass.data[DOMAIN][DATA].devices[config_entry.entry_id].coordinator

    config_entry.async_on_unload(
        async_track_entity_registry_updated_event(
            hass, config_entry.entry_id, async_registry_updated
        )
    )

    device: BatteryNotesDevice = hass.data[DOMAIN][DATA].devices[config_entry.entry_id]

    if not device.fake_device:
        device_id = async_add_to_device(hass, config_entry)

        if not device_id:
            return

    description = BatteryNotesBinarySensorEntityDescription(
        unique_id_suffix="_battery_low",
        key="_battery_plus_low",
        translation_key="battery_low",
        icon="mdi:battery-alert",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.BATTERY,
    )

    device: BatteryNotesDevice = hass.data[DOMAIN][DATA].devices[config_entry.entry_id]

    if coordinator.battery_low_template is not None:
        async_add_entities(
            [
                BatteryNotesBatteryLowTemplateSensor(
                    hass,
                    coordinator,
                    description,
                    f"{config_entry.entry_id}{description.unique_id_suffix}",
                    coordinator.battery_low_template,
                )
            ]
        )

    elif device.wrapped_battery is not None:
        async_add_entities(
            [
                BatteryNotesBatteryLowSensor(
                    hass,
                    coordinator,
                    description,
                    f"{config_entry.entry_id}{description.unique_id_suffix}",
                )
            ]
        )


async def async_setup_platform(
    hass: HomeAssistant,
) -> None:
    """Set up the battery note sensor."""

    await async_setup_reload_service(hass, DOMAIN, PLATFORMS)

class _TemplateAttribute:
    """Attribute value linked to template result."""

    def __init__(
        self,
        entity: Entity,
        attribute: str,
        template: Template,
        validator: Callable[[Any], Any] | None = None,
        on_update: Callable[[Any], None] | None = None,
        none_on_template_error: bool | None = False,
    ) -> None:
        """Template attribute."""
        self._entity = entity
        self._attribute = attribute
        self.template = template
        self.validator = validator
        self.on_update = on_update
        self.async_update = None
        self.none_on_template_error = none_on_template_error

    @callback
    def async_setup(self) -> None:
        """Config update path for the attribute."""
        if self.on_update:
            return

        if not hasattr(self._entity, self._attribute):
            raise AttributeError(f"Attribute '{self._attribute}' does not exist.")

        self.on_update = self._default_update

    @callback
    def _default_update(self, result: str | TemplateError) -> None:
        attr_result = None if isinstance(result, TemplateError) else result
        setattr(self._entity, self._attribute, attr_result)

    @callback
    def handle_result(
        self,
        event: Event[EventStateChangedData] | None,
        template: Template,
        last_result: str | None | TemplateError,
        result: str | TemplateError,
    ) -> None:
        """Handle a template result event callback."""
        if isinstance(result, TemplateError):
            _LOGGER.error(
                (
                    "TemplateError('%s') "
                    "while processing template '%s' "
                    "for attribute '%s' in entity '%s'"
                ),
                result,
                self.template,
                self._attribute,
                self._entity.entity_id,
            )
            if self.none_on_template_error:
                self._default_update(result)
            else:
                assert self.on_update
                self.on_update(result)
            return

        if not self.validator:
            assert self.on_update
            self.on_update(result)
            return

        try:
            validated = self.validator(result)
        except vol.Invalid as ex:
            _LOGGER.error(
                (
                    "Error validating template result '%s' "
                    "from template '%s' "
                    "for attribute '%s' in entity %s "
                    "validation message '%s'"
                ),
                result,
                self.template,
                self._attribute,
                self._entity.entity_id,
                ex.msg,
            )
            assert self.on_update
            self.on_update(None)
            return

        assert self.on_update
        self.on_update(validated)
        return

class BatteryNotesBatteryLowTemplateSensor(BinarySensorEntity, CoordinatorEntity[BatteryNotesCoordinator]):
    """Represents a low battery threshold binary sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesBinarySensorEntityDescription,
        unique_id: str,
        template: str,
    ) -> None:
        """Create a low battery binary sensor."""

        device_registry = dr.async_get(hass)

        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = unique_id
        self._template_attrs: dict[Template, list[_TemplateAttribute]] = {}

        super().__init__(coordinator=coordinator)

        if coordinator.device_id and (
            device_entry := device_registry.async_get(coordinator.device_id)
        ):
            self._attr_device_info = DeviceInfo(
                connections=device_entry.connections,
                identifiers=device_entry.identifiers,
            )

        self._attr_has_entity_name = True

        if coordinator.source_entity_id and not coordinator.device_id:
            self._attr_translation_placeholders = {"device_name": coordinator.device_name + " "}
            self.entity_id = f"binary_sensor.{coordinator.device_name.lower()}_{description.key}"
        elif coordinator.source_entity_id and coordinator.device_id:
            source_entity_domain, source_object_id = split_entity_id(coordinator.source_entity_id)
            self._attr_translation_placeholders = {"device_name": coordinator.source_entity_name + " "}
            self.entity_id = f"binary_sensor.{source_object_id}_{description.key}"
        else:
            self._attr_translation_placeholders = {"device_name": ""}
            self.entity_id = f"binary_sensor.{coordinator.device_name.lower()}_{description.key}"

        self._template = template
        self._state: bool | None = None

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        await super().async_added_to_hass()

        self._async_setup_templates()

        async_at_start(self.hass, self._async_template_startup)

    def add_template_attribute(
        self,
        attribute: str,
        template: Template,
        validator: Callable[[Any], Any] | None = None,
        on_update: Callable[[Any], None] | None = None,
        none_on_template_error: bool = False,
    ) -> None:
        """Call in the constructor to add a template linked to a attribute.

        Parameters
        ----------
        attribute
            The name of the attribute to link to. This attribute must exist
            unless a custom on_update method is supplied.
        template
            The template to calculate.
        validator
            Validator function to parse the result and ensure it's valid.
        on_update
            Called to store the template result rather than storing it
            the supplied attribute. Passed the result of the validator, or None
            if the template or validator resulted in an error.
        none_on_template_error
            If True, the attribute will be set to None if the template errors.

        """
        assert self.hass is not None, "hass cannot be None"
        template.hass = self.hass
        template_attribute = _TemplateAttribute(
            self, attribute, template, validator, on_update, none_on_template_error
        )
        self._template_attrs.setdefault(template, [])
        self._template_attrs[template].append(template_attribute)

    @callback
    def _async_setup_templates(self) -> None:
        """Set up templates."""
        self.add_template_attribute("_state", Template(self._template), None, self._update_state)

    @callback
    def _async_template_startup(
        self,
        _hass: HomeAssistant | None,
        log_fn: Callable[[int, str], None] | None = None,
    ) -> None:
        template_var_tups: list[TrackTemplate] = []
        has_availability_template = False

        variables = {"this": TemplateStateFromEntityId(self.hass, self.entity_id)}

        for loop_template, attributes in self._template_attrs.items():
            template_var_tup = TrackTemplate(loop_template, variables)
            is_availability_template = False
            for attribute in attributes:
                # pylint: disable-next=protected-access
                if attribute._attribute == "_attr_available":
                    has_availability_template = True
                    is_availability_template = True
                attribute.async_setup()
            # Insert the availability template first in the list
            if is_availability_template:
                template_var_tups.insert(0, template_var_tup)
            else:
                template_var_tups.append(template_var_tup)

        result_info = async_track_template_result(
            self.hass,
            template_var_tups,
            self._handle_results,
            log_fn=log_fn,
            has_super_template=has_availability_template,
        )
        self.async_on_remove(result_info.async_remove)
        self._template_result_info = result_info
        result_info.async_refresh()

    @callback
    def _handle_results(
        self,
        event: Event[EventStateChangedData] | None,
        updates: list[TrackTemplateResult],
    ) -> None:
        """Call back the results to the attributes."""
        if event:
            self.async_set_context(event.context)

        entity_id = event and event.data["entity_id"]

        if entity_id and entity_id == self.entity_id:
            self._self_ref_update_count += 1
        else:
            self._self_ref_update_count = 0

        if self._self_ref_update_count > len(self._template_attrs):
            for update in updates:
                _LOGGER.warning(
                    (
                        "Template loop detected while processing event: %s, skipping"
                        " template render for Template[%s]"
                    ),
                    event,
                    update.template.template,
                )
            return

        for update in updates:
            for template_attr in self._template_attrs[update.template]:
                template_attr.handle_result(
                    event, update.template, update.last_result, update.result
                )

        self.async_write_ha_state()
        return


    @callback
    def _update_state(self, result):

        state = (
            None
            if isinstance(result, TemplateError)
            else template.result_as_boolean(result)
        )

        if state == self._state:
            return

        self._state = state
        self.coordinator.battery_low_template_state = state
        _LOGGER.debug("%s binary sensor battery_low set to: %s via template", self.entity_id, state)


    @property
    def is_on(self) -> bool | None:
        """Return true if sensor is on."""
        return self._state

class BatteryNotesBatteryLowSensor(BinarySensorEntity, CoordinatorEntity[BatteryNotesCoordinator]):
    """Represents a low battery threshold binary sensor."""

    _attr_should_poll = False

    def __init__(
        self,
        hass: HomeAssistant,
        coordinator: BatteryNotesCoordinator,
        description: BatteryNotesBinarySensorEntityDescription,
        unique_id: str,
    ) -> None:
        """Create a low battery binary sensor."""

        device_registry = dr.async_get(hass)

        self.coordinator = coordinator
        self._attr_has_entity_name = True

        if coordinator.source_entity_id and not coordinator.device_id:
            self._attr_translation_placeholders = {"device_name": coordinator.device_name + " "}
            self.entity_id = f"binary_sensor.{coordinator.device_name.lower()}_{description.key}"
        elif coordinator.source_entity_id and coordinator.device_id:
            source_entity_domain, source_object_id = split_entity_id(coordinator.source_entity_id)
            self._attr_translation_placeholders = {"device_name": coordinator.source_entity_name + " "}
            self.entity_id = f"binary_sensor.{source_object_id}_{description.key}"
        else:
            self._attr_translation_placeholders = {"device_name": ""}
            self.entity_id = f"binary_sensor.{coordinator.device_name.lower()}_{description.key}"

        self.entity_description = description
        self._attr_unique_id = unique_id

        super().__init__(coordinator=coordinator)

        if coordinator.device_id and (
            device_entry := device_registry.async_get(coordinator.device_id)
        ):
            self._attr_device_info = DeviceInfo(
                connections=device_entry.connections,
                identifiers=device_entry.identifiers,
            )

    async def async_added_to_hass(self) -> None:
        """Handle added to Hass."""

        await super().async_added_to_hass()

        await self.coordinator.async_config_entry_first_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""

        if (
            (
                wrapped_battery_state := self.hass.states.get(
                    self.coordinator.wrapped_battery.entity_id
                )
            )
            is None
            or wrapped_battery_state.state
            in [
                STATE_UNAVAILABLE,
                STATE_UNKNOWN,
            ]
            or not validate_is_float(wrapped_battery_state.state)
        ):
            self._attr_is_on = None
            self._attr_available = False
            self.async_write_ha_state()
            return

        self._attr_is_on = self.coordinator.battery_low

        self.async_write_ha_state()

        _LOGGER.debug("%s binary sensor battery_low set to: %s", self.coordinator.wrapped_battery.entity_id, self.coordinator.battery_low)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes of battery low."""

        attrs = {
            ATTR_BATTERY_LOW_THRESHOLD: self.coordinator.battery_low_threshold,
        }

        super_attrs = super().extra_state_attributes
        if super_attrs:
            attrs.update(super_attrs)
        return attrs

"""Template helpers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import voluptuous as vol

from homeassistant.core import (
    Event,
    HomeAssistant,
    callback,
)
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    EventStateChangedData,
    TrackTemplate,
    TrackTemplateResult,
    TrackTemplateResultInfo,
    async_track_template_result,
)
from homeassistant.helpers.start import async_at_start
from homeassistant.helpers.template import Template, TemplateStateFromEntityId

_LOGGER = logging.getLogger(__name__)


class _TemplateAttribute:
    """Attribute value linked to template result."""

    def __init__(  # noqa: PLR0913
        self,
        entity: Entity,
        attribute: str,
        tmpl: Template,
        validator: Callable[[Any], Any] | None = None,
        on_update: Callable[[Any], None] | None = None,
        none_on_template_error: bool | None = False,
    ) -> None:
        """Template attribute."""
        self._entity = entity
        self._attribute = attribute
        self.template = tmpl
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
        event: Event[EventStateChangedData] | None,  # noqa: ARG002
        tmpl: Template,  # noqa: ARG002
        last_result: str | None | TemplateError,  # noqa: ARG002
        result: str | TemplateError,
    ) -> None:
        # pylint: disable=unused-argument
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


class TemplateTrackingMixin(Entity):
    """Track a template rendering the entity state, calling _update_state with results."""

    _template: str
    _template_attrs: dict[Template, list[_TemplateAttribute]]
    _template_result_info: TrackTemplateResultInfo | None
    _self_ref_update_count = 0

    def _init_template_tracking(self, template: str) -> None:
        """Set the template to track, call from the constructor."""
        self._template = template
        self._template_attrs = {}
        self._template_result_info = None

    @callback
    def _async_start_template_tracking(self) -> None:
        """Start tracking the template once Home Assistant has started."""
        self._async_setup_templates()
        self.async_on_remove(async_at_start(self.hass, self._async_template_startup))

    @callback
    def _update_state(self, result: Any) -> None:
        """Handle a template result."""
        raise NotImplementedError

    @callback
    def _async_write_template_state(self) -> None:
        """Write the state after handling template results."""
        self.async_write_ha_state()

    def add_template_attribute(
        self,
        attribute: str,
        tmpl: Template,
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
        tmpl
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
        tmpl.hass = self.hass
        template_attribute = _TemplateAttribute(
            self, attribute, tmpl, validator, on_update, none_on_template_error
        )
        self._template_attrs.setdefault(tmpl, [])
        self._template_attrs[tmpl].append(template_attribute)

    @callback
    def _async_setup_templates(self) -> None:
        """Set up templates."""
        self.add_template_attribute(
            "_state", Template(self._template, self.hass), None, self._update_state
        )

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
                if attribute._attribute == "_attr_available":  # noqa: SLF001
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

        self._async_write_template_state()

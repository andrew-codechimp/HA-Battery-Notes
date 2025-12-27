"""Template helpers."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import voluptuous as vol

from homeassistant.core import (
    Event,
    callback,
)
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    EventStateChangedData,
)
from homeassistant.helpers.template import Template

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

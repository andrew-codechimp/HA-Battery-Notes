"""Resolve device-scoped entity placeholders in templates."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from jinja2 import Environment, TemplateSyntaxError

from homeassistant.const import (
    ATTR_DEVICE_CLASS,
    ATTR_UNIT_OF_MEASUREMENT,
    PERCENTAGE,
    Platform,
)
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    EventStateChangedData,
    async_track_state_change_event,
)

from .const import DOMAIN

_PLACEHOLDER = re.compile(
    r"\[\[(?P<scope>[a-z_]+)::(?P<selector>[^\]\n]*)\]\]", re.IGNORECASE
)
_PLACEHOLDER_START = re.compile(r"\[\[[a-z_]+:", re.IGNORECASE)
_LEXER = Environment(autoescape=True, keep_trailing_newline=True)


@dataclass(frozen=True)
class SourceSelector:
    """Describe a source independently of template syntax and registry state."""

    domain: Platform
    device_class: str
    unit: str | None = None

    @classmethod
    def parse(cls, selector: str) -> Self:
        """Parse the device-scoped selector fields."""
        parts = selector.casefold().split(":")
        if (
            len(parts) not in (2, 3)
            or parts[0] not in (Platform.SENSOR, Platform.BINARY_SENSOR)
            or not re.fullmatch(r"[a-z_][a-z0-9_]*", parts[1])
            or (len(parts) == 3 and not parts[2])
        ):
            raise TemplateError(f"Invalid source placeholder: [[source::{selector}]]")
        unit = parts[2] if len(parts) == 3 else None
        if unit == "percentage":
            unit = PERCENTAGE
        return cls(Platform(parts[0]), parts[1], unit)

    def __str__(self) -> str:
        """Describe the selector in resolution errors."""
        unit = f":{self.unit}" if self.unit is not None else ""
        return f"[[source::{self.domain}:{self.device_class}{unit}]]"


_SELECTOR_PARSERS = {"source": SourceSelector.parse}


@dataclass(frozen=True)
class ParsedTemplate:
    """Keep source spans and parsed selectors without rewriting Jinja syntax."""

    parts: tuple[str | SourceSelector, ...]

    @property
    def has_placeholders(self) -> bool:
        """Return whether this template needs source resolution."""
        return any(isinstance(part, SourceSelector) for part in self.parts)

    @classmethod
    def parse(cls, template: str) -> Self:
        """Find whole placeholder string tokens, leaving comments and data intact."""
        source = template.replace("\r\n", "\n").replace("\r", "\n")
        parts: list[str | SourceSelector] = []
        cursor = copied = 0
        try:
            tokens = list(_LEXER.lex(source))
        except TemplateSyntaxError as ex:
            raise TemplateError(ex) from ex
        for _line, kind, value in tokens:
            start = source.index(value, cursor)
            cursor = start + len(value)
            if kind != "string" or not _PLACEHOLDER_START.search(value):
                continue
            match = _PLACEHOLDER.fullmatch(value[1:-1])
            if match is None:
                raise TemplateError(
                    "Placeholders must use [[namespace::selector]] as a whole quoted entity ID"
                )
            scope = match["scope"].casefold()
            if (parser := _SELECTOR_PARSERS.get(scope)) is None:
                raise TemplateError(f"Unsupported placeholder scope: {scope}")
            parts.extend((source[copied:start], parser(match["selector"])))
            copied = cursor
        if not parts:
            return cls((template,))
        parts.append(source[copied:])
        return cls(tuple(parts))


class SourceTemplateResolver:
    """Resolve placeholders and observe changes to their candidate entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        template: ParsedTemplate,
        device_id: str | None,
        source_entity_id: str | None,
        on_change: Callable[[], None],
    ) -> None:
        """Keep the configured source identity across entity renames."""
        self._hass = hass
        self._template = template
        self._registry = er.async_get(hass)
        self._device_id = device_id
        source = (
            self._registry.async_get(source_entity_id) if source_entity_id else None
        )
        self._source_id = source.id if source else source_entity_id
        self._on_change = on_change
        self._entity_ids: set[str] = set()
        self._remove_state_listener: CALLBACK_TYPE | None = None

    def _candidates(self) -> list[er.RegistryEntry]:
        """Use an entity note's current device, or just its standalone source."""
        device_id = self._device_id
        if self._source_id:
            if not (source := self._registry.async_get(self._source_id)):
                return []
            device_id = source.device_id
            if device_id is None:
                return [source] if source.platform != DOMAIN else []
        if device_id is None:
            return []
        return [
            entry
            for entry in er.async_entries_for_device(self._registry, device_id)
            if entry.platform != DOMAIN
        ]

    def resolve(self) -> str:
        """Replace quoted placeholders with exactly one matching entity ID."""
        candidates = self._candidates()
        resolved: dict[SourceSelector, str] = {}
        parts = []
        for part in self._template.parts:
            if isinstance(part, str):
                parts.append(part)
                continue
            if part not in resolved:
                resolved[part] = repr(self._resolve_source(part, candidates))
            parts.append(resolved[part])
        return "".join(parts)

    def _resolve_source(
        self, selector: SourceSelector, candidates: list[er.RegistryEntry]
    ) -> str:
        """Match one parsed selector against the note's source candidates."""
        matches = []
        for entry in candidates:
            if entry.disabled or entry.domain != selector.domain:
                continue
            state = self._hass.states.get(entry.entity_id)
            attributes = state.attributes if state else {}
            entry_class = (
                entry.device_class
                or entry.original_device_class
                or attributes.get(ATTR_DEVICE_CLASS)
            )
            entry_unit = attributes.get(
                ATTR_UNIT_OF_MEASUREMENT, entry.unit_of_measurement
            )
            if (
                entry_class is not None
                and entry_class.casefold() == selector.device_class
                and (
                    selector.unit is None
                    or (
                        entry_unit is not None
                        and entry_unit.casefold() == selector.unit
                    )
                )
            ):
                matches.append(entry.entity_id)
        if not matches:
            raise TemplateError(f"No entity matches source placeholder {selector}")
        if len(matches) > 1:
            raise TemplateError(
                f"Ambiguous source placeholder {selector}: {', '.join(sorted(matches))}"
            )
        return matches[0]

    @callback
    def async_start(self) -> CALLBACK_TYPE:
        """Watch registry membership and live source metadata, with one cleanup."""
        self._watch_states()
        remove_registry_listener = self._hass.bus.async_listen(
            er.EVENT_ENTITY_REGISTRY_UPDATED, self._registry_updated
        )

        @callback
        def remove() -> None:
            remove_registry_listener()
            if self._remove_state_listener:
                self._remove_state_listener()
                self._remove_state_listener = None

        return remove

    @callback
    def _watch_states(self) -> None:
        if self._remove_state_listener:
            self._remove_state_listener()
        self._entity_ids = {entry.entity_id for entry in self._candidates()}
        self._remove_state_listener = async_track_state_change_event(
            self._hass, self._entity_ids, self._state_changed
        )

    @callback
    def _registry_updated(
        self, event: Event[er.EventEntityRegistryUpdatedData]
    ) -> None:
        entity_id = event.data["entity_id"]
        entry = self._registry.async_get(entity_id)
        if entry and entry.platform == DOMAIN:
            return
        current_ids = {candidate.entity_id for candidate in self._candidates()}
        old_entity_id = event.data.get("old_entity_id")
        if (
            entity_id not in self._entity_ids | current_ids
            and old_entity_id not in self._entity_ids
        ):
            return
        self._watch_states()
        self._on_change()

    @callback
    def _state_changed(self, event: Event[EventStateChangedData]) -> None:
        old_state = event.data["old_state"]
        new_state = event.data["new_state"]
        old_attributes = old_state.attributes if old_state else {}
        new_attributes = new_state.attributes if new_state else {}
        if any(
            old_attributes.get(key) != new_attributes.get(key)
            for key in (ATTR_DEVICE_CLASS, ATTR_UNIT_OF_MEASUREMENT)
        ):
            self._on_change()

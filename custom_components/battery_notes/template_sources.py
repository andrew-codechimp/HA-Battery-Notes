"""Resolve device-scoped source calls in templates."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from jinja2 import Environment, TemplateSyntaxError, nodes

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

_SOURCE_FUNCTION = "battery_notes_source"
_LEXER = Environment(autoescape=True, keep_trailing_newline=True)


@dataclass(frozen=True)
class SourceSelector:
    """Describe a source independently of template syntax and registry state."""

    domain: Platform
    device_class: str
    unit: str | None = None

    @classmethod
    def parse(cls, expression: str) -> Self:
        """Parse a source call with two or three literal string arguments."""
        output = _LEXER.parse("{{ " + expression + " }}").body[0]
        if TYPE_CHECKING:
            assert isinstance(output, nodes.Output)
        call = output.nodes[0]
        if not isinstance(call, nodes.Call):
            raise TemplateError("Invalid battery_notes_source() call")
        parts = [
            arg.value.casefold()
            for arg in call.args
            if isinstance(arg, nodes.Const) and isinstance(arg.value, str)
        ]
        if (
            len(call.args) not in (2, 3)
            or call.kwargs
            or call.dyn_args is not None
            or call.dyn_kwargs is not None
            or len(parts) != len(call.args)
        ):
            raise TemplateError(
                "battery_notes_source() requires two or three literal string arguments"
            )
        if (
            parts[0] not in (Platform.SENSOR, Platform.BINARY_SENSOR)
            or not re.fullmatch(r"[a-z_][a-z0-9_]*", parts[1])
            or (len(parts) == 3 and not parts[2])
        ):
            raise TemplateError(f"Invalid source selector: {expression}")
        unit = parts[2] if len(parts) == 3 else None
        if unit == "percentage":
            unit = PERCENTAGE
        return cls(Platform(parts[0]), parts[1], unit)

    def __str__(self) -> str:
        """Describe the selector in resolution errors."""
        args = [self.domain.value, self.device_class]
        if self.unit is not None:
            args.append(self.unit)
        return f"{_SOURCE_FUNCTION}({', '.join(repr(arg) for arg in args)})"


@dataclass(frozen=True)
class ParsedTemplate:
    """Keep source spans and parsed selectors without rewriting Jinja syntax."""

    parts: tuple[str | SourceSelector, ...]

    @property
    def has_sources(self) -> bool:
        """Return whether this template needs source resolution."""
        return any(isinstance(part, SourceSelector) for part in self.parts)

    @classmethod
    def parse(cls, template: str) -> Self:
        """Find source calls, leaving strings, comments, and data intact."""
        source = template.replace("\r\n", "\n").replace("\r", "\n")
        parts: list[str | SourceSelector] = []
        cursor = copied = 0
        previous = before_previous = ""
        try:
            tokens = list(_LEXER.lex(source))
            index = 0
            while index < len(tokens):
                _line, kind, value = tokens[index]
                start = source.index(value, cursor)
                cursor = start + len(value)
                index += 1
                if kind == "whitespace":
                    continue
                is_source = (
                    kind == "name"
                    and value == _SOURCE_FUNCTION
                    and previous not in (".", "|", "is", "macro", "filter")
                    and (before_previous, previous) != ("is", "not")
                )
                before_previous, previous = previous, value
                if not is_source:
                    continue
                while index < len(tokens) and tokens[index][1] == "whitespace":
                    index += 1
                if index == len(tokens) or tokens[index][2] != "(":
                    continue
                depth = 0
                for _line, call_kind, call_value in tokens[index:]:
                    call_start = source.index(call_value, cursor)
                    cursor = call_start + len(call_value)
                    index += 1
                    if call_kind == "operator":
                        if call_value == "(":
                            depth += 1
                        elif call_value == ")":
                            depth -= 1
                            if depth == 0:
                                break
                parts.extend(
                    (source[copied:start], SourceSelector.parse(source[start:cursor]))
                )
                copied = cursor
                previous = ")"
        except TemplateSyntaxError as ex:
            raise TemplateError(ex) from ex
        if not parts:
            return cls((template,))
        parts.append(source[copied:])
        return cls(tuple(parts))


class SourceTemplateResolver:
    """Resolve source calls and observe changes to their candidate entities."""

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
        """Replace source calls with exactly one matching entity ID."""
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
            raise TemplateError(f"No entity matches source selector {selector}")
        if len(matches) > 1:
            raise TemplateError(
                f"Ambiguous source selector {selector}: {', '.join(sorted(matches))}"
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

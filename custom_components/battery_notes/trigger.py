"""Automation triggers for Battery Notes."""

from collections.abc import Callable, Mapping
from typing import Any, cast, override

import voluptuous as vol

from homeassistant.const import CONF_OPTIONS, CONF_TARGET
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.target import (
    TargetSelection,
    async_extract_referenced_entity_ids,
)
from homeassistant.helpers.trigger import (
    Trigger,
    TriggerActionRunner,
    TriggerConfig,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    ATTR_DEVICE_ID,
    ATTR_SOURCE_ENTITY_ID,
    DOMAIN,
    EVENT_BATTERY_INCREASED,
    EVENT_BATTERY_NOT_REPLACED,
    EVENT_BATTERY_NOT_REPORTED,
    EVENT_BATTERY_REPLACED,
    EVENT_BATTERY_THRESHOLD,
)
from .coordinator import BatteryNotesConfigEntry

CONF_EVENT_TYPES = "event_types"

BATTERY_NOTES_TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default={}): {},
    }
)

BATTERY_BECAME_LOW_TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_TARGET): cv.TARGET_FIELDS,
        vol.Required(CONF_OPTIONS, default={}): {
            vol.Required(CONF_EVENT_TYPES, default="all"): vol.In(
                ["all", "low_state_transitions", "reminders"]
            ),
        },
    }
)


class BatteryNotesTrigger(Trigger):
    """Base trigger matching Battery Notes event sources against targets."""

    def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
        """Initialize the event target selection."""
        super().__init__(hass, config)
        self._target = (
            TargetSelection(config.target) if config.target is not None else None
        )

    @callback
    def _matches_target(self, data: Mapping[str, Any]) -> bool:
        """Match event sources and Battery Notes entities against current targets."""
        if self._target is None:
            return True

        selected = async_extract_referenced_entity_ids(
            self._hass, self._target, primary_entities_only=False
        )
        device_id = data.get(ATTR_DEVICE_ID)
        source_entity_id = data.get(ATTR_SOURCE_ENTITY_ID)
        if device_id and device_id in selected.referenced_devices:
            return True

        entity_ids = selected.referenced | selected.indirectly_referenced
        if source_entity_id and source_entity_id in entity_ids:
            return True

        registry = er.async_get(self._hass)
        for entity_id in entity_ids:
            if (entity := registry.async_get(entity_id)) is None:
                continue
            if entity.platform != DOMAIN:
                if not source_entity_id and device_id and entity.device_id == device_id:
                    return True
                continue
            if not entity.config_entry_id or not entity.config_subentry_id:
                continue
            entry = self._hass.config_entries.async_get_entry(entity.config_entry_id)
            if entry is None or not hasattr(entry, "runtime_data"):
                continue
            coordinators = cast(
                BatteryNotesConfigEntry, entry
            ).runtime_data.subentry_coordinators
            coordinator = (coordinators or {}).get(entity.config_subentry_id)
            if coordinator is not None and (
                (coordinator.source_entity_id or "") == (source_entity_id or "")
                and (coordinator.device_id or "") == (device_id or "")
            ):
                return True
        return False


class BatteryNotesEventTrigger(BatteryNotesTrigger):
    """Trigger on a targeted Battery Notes event without additional options."""

    _event_type: str
    _description: str

    @classmethod
    @override
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate the trigger configuration."""
        return cast(ConfigType, BATTERY_NOTES_TRIGGER_SCHEMA(config))

    @override
    async def async_attach_runner(
        self,
        run_action: TriggerActionRunner,
        _did_not_trigger: Callable[..., None] | None = None,
    ) -> CALLBACK_TYPE:
        """Listen for matching events and forward their data to the action."""

        @callback
        def async_battery_event(event: Event) -> None:
            """Handle a Battery Notes event."""
            if self._matches_target(event.data):
                run_action(
                    dict(event.data),
                    self._description,
                    event.context,
                )

        return self._hass.bus.async_listen(self._event_type, async_battery_event)


class BatteryWasReplacedTrigger(BatteryNotesEventTrigger):
    """Trigger when a targeted battery note raises a replacement event."""

    _event_type = EVENT_BATTERY_REPLACED
    _description = "battery replaced"


class BatteryHasIncreasedTrigger(BatteryNotesEventTrigger):
    """Trigger when a targeted battery note raises an increased event."""

    _event_type = EVENT_BATTERY_INCREASED
    _description = "battery has increased"


class BatteryWasNotReportedTrigger(BatteryNotesEventTrigger):
    """Trigger on events raised by the check battery last reported action."""

    _event_type = EVENT_BATTERY_NOT_REPORTED
    _description = "battery was not reported"


class BatteryWasNotReplacedTrigger(BatteryNotesEventTrigger):
    """Trigger on events raised by the check battery last replaced action."""

    _event_type = EVENT_BATTERY_NOT_REPLACED
    _description = "battery was not replaced"


class BatteryBecameLowTrigger(BatteryNotesTrigger):
    """Trigger on low battery threshold events with optional reminders."""

    @classmethod
    @override
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate the trigger configuration."""
        return cast(ConfigType, BATTERY_BECAME_LOW_TRIGGER_SCHEMA(config))

    def __init__(self, hass: HomeAssistant, config: TriggerConfig) -> None:
        """Initialize the low battery trigger."""
        super().__init__(hass, config)
        self._event_types = (config.options or {})[CONF_EVENT_TYPES]

    @override
    async def async_attach_runner(
        self,
        run_action: TriggerActionRunner,
        _did_not_trigger: Callable[..., None] | None = None,
    ) -> CALLBACK_TYPE:
        """Listen for matching low battery events."""

        @callback
        def async_battery_low(event: Event) -> None:
            """Handle a battery threshold event."""
            if not event.data[ATTR_BATTERY_LOW]:
                return
            reminder = event.data[ATTR_BATTERY_THRESHOLD_REMINDER]
            if (self._event_types == "low_state_transitions" and reminder) or (
                self._event_types == "reminders" and not reminder
            ):
                return
            if self._matches_target(event.data):
                run_action(dict(event.data), "battery low", event.context)

        return self._hass.bus.async_listen(EVENT_BATTERY_THRESHOLD, async_battery_low)


class BatteryNoLongerLowTrigger(BatteryNotesTrigger):
    """Trigger when a battery threshold event indicates the battery is healthy."""

    @classmethod
    @override
    async def async_validate_config(
        cls, hass: HomeAssistant, config: ConfigType
    ) -> ConfigType:
        """Validate the trigger configuration."""
        return cast(ConfigType, BATTERY_NOTES_TRIGGER_SCHEMA(config))

    @override
    async def async_attach_runner(
        self,
        run_action: TriggerActionRunner,
        _did_not_trigger: Callable[..., None] | None = None,
    ) -> CALLBACK_TYPE:
        """Listen for matching healthy battery threshold events."""

        @callback
        def async_battery_no_longer_low(event: Event) -> None:
            """Handle a battery threshold event."""
            if not event.data[ATTR_BATTERY_LOW] and self._matches_target(event.data):
                run_action(dict(event.data), "battery no longer low", event.context)

        return self._hass.bus.async_listen(
            EVENT_BATTERY_THRESHOLD, async_battery_no_longer_low
        )


async def async_get_triggers(hass: HomeAssistant) -> dict[str, type[Trigger]]:  # noqa: ARG001
    """Return the triggers provided by Battery Notes."""
    return {
        "battery_was_replaced": BatteryWasReplacedTrigger,
        "battery_has_increased": BatteryHasIncreasedTrigger,
        "battery_became_low": BatteryBecameLowTrigger,
        "battery_no_longer_low": BatteryNoLongerLowTrigger,
        "battery_was_not_reported": BatteryWasNotReportedTrigger,
        "battery_was_not_replaced": BatteryWasNotReplacedTrigger,
    }

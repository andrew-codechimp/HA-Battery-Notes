"""Automation triggers for Battery Notes."""

from collections.abc import Callable
from typing import cast, override

import voluptuous as vol

from homeassistant.const import CONF_OPTIONS
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.helpers.trigger import (
    Trigger,
    TriggerActionRunner,
    TriggerConfig,
)
from homeassistant.helpers.typing import ConfigType

from .const import (
    ATTR_BATTERY_LOW,
    ATTR_BATTERY_THRESHOLD_REMINDER,
    EVENT_BATTERY_INCREASED,
    EVENT_BATTERY_NOT_REPLACED,
    EVENT_BATTERY_NOT_REPORTED,
    EVENT_BATTERY_REPLACED,
    EVENT_BATTERY_THRESHOLD,
)

CONF_EVENT_TYPES = "event_types"

BATTERY_NOTES_TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OPTIONS, default={}): {},
    }
)

BATTERY_BECAME_LOW_TRIGGER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OPTIONS, default={}): {
            vol.Required(CONF_EVENT_TYPES, default="all"): vol.In(
                [
                    "all",
                    "low_state_transitions",
                    "reminders",
                ]
            ),
        },
    }
)


class BatteryNotesEventTrigger(Trigger):
    """Trigger on a Battery Notes event."""

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
            run_action(dict(event.data), self._description, event.context)

        return self._hass.bus.async_listen(self._event_type, async_battery_event)


class BatteryWasReplacedTrigger(BatteryNotesEventTrigger):
    """Trigger when a battery note raises a replacement event."""

    _event_type = EVENT_BATTERY_REPLACED
    _description = "battery replaced"


class BatteryHasIncreasedTrigger(BatteryNotesEventTrigger):
    """Trigger when a battery note raises an increased event."""

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


class BatteryBecameLowTrigger(Trigger):
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
            run_action(dict(event.data), "battery low", event.context)

        return self._hass.bus.async_listen(EVENT_BATTERY_THRESHOLD, async_battery_low)


class BatteryNoLongerLowTrigger(Trigger):
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
            if not event.data[ATTR_BATTERY_LOW]:
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

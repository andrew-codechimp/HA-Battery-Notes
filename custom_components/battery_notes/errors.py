"""Errors for battery types component."""

from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class BatteryNotesSetupError(HomeAssistantError):
    """Raised when an error occured during  sensor setup."""


class SensorConfigurationError(BatteryNotesSetupError):
    """Raised when sensor configuration is invalid."""


class SensorAlreadyConfiguredError(SensorConfigurationError):
    """Raised when battery types has already been configured before for the entity."""

    def __init__(
        self,
        source_entity_id: str,
        existing_entities: list,
    ) -> None:
        """Existing battery type configured."""
        self.existing_entities = existing_entities
        super().__init__(
            f"{source_entity_id}: This entity has already configured a battery type. ",
        )

    def get_existing_entities(self) -> list:
        """Get existing entities."""
        return self.existing_entities

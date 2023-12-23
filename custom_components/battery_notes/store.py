"""Data store for battery_notes."""
from __future__ import annotations

import logging
import attr
from collections import OrderedDict
from typing import MutableMapping, cast
from datetime import date
from dataclasses import dataclass

from homeassistant.core import (callback, HomeAssistant)
from homeassistant.loader import bind_hass
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DATA_REGISTRY = f"{DOMAIN}_storage"
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION_MAJOR = 1
STORAGE_VERSION_MINOR = 0
SAVE_DELAY = 10

@attr.s(slots=True, frozen=True)
class LastChangedEntry:
    """Last Changed storage Entry."""

    entity_id = attr.ib(type=str, default=None)
    last_changed = attr.ib(type=date, default=None)

class MigratableStore(Store):
    """Holds battery notes data."""

    async def _async_migrate_func(self, old_major_version: int, old_minor_version: int, data: dict):

        # if old_major_version == 1:
            # Do nothing for now

        return data


class BatteryNotesStorage:
    """Class to hold battery notes data."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the storage."""
        self.hass = hass
        self.last_changed_entities: MutableMapping[str, LastChangedEntry] = {}
        self._store = MigratableStore(hass, STORAGE_VERSION_MAJOR, STORAGE_KEY, minor_version=STORAGE_VERSION_MINOR)

    async def async_load(self) -> None:
        """Load the registry of schedule entries."""
        data = await self._store.async_load()
        last_changed_entities: "OrderedDict[str, LastChangedEntry]" = OrderedDict()

        if data is not None:
            if "last_changed_entities" in data:
                for entity in data["last_changed_entities"]:
                    last_changed_entities[entity["entity_id"]] = LastChangedEntry(**entity)

        self.last_changed_entities = last_changed_entities

    @callback
    def async_schedule_save(self) -> None:
        """Schedule saving the registry."""
        self._store.async_delay_save(self._data_to_save, SAVE_DELAY)

    async def async_save(self) -> None:
        """Save the registry."""
        await self._store.async_save(self._data_to_save())

    @callback
    def _data_to_save(self) -> dict:
        """Return data for the registry to store in a file."""
        store_data = {}

        store_data["devices"] = [
            attr.asdict(entry) for entry in self.sensors.values()
        ]

        return store_data

    async def async_delete(self):
        """Delete data."""
        _LOGGER.warning("Removing battery notes data!")
        await self._store.async_remove()
        self.last_changed_entities = {}
        await self.async_factory_default()


    @callback
    def async_get_last_changed(self, entity_id) -> LastChangedEntry:
        """Get an existing DeviceEntry by id."""
        res = self.last_changed_entities.get(entity_id)
        return attr.asdict(res) if res else None

    @callback
    def async_get_last_changed(self):
        """Get an existing LastChangedEntry by id."""
        res = {}
        for (key, val) in self.last_changed_entities.items():
            res[key] = attr.asdict(val)
        return res

    @callback
    def async_create_last_changed(self, entity_id: str, data: dict) -> LastChangedEntry:
        """Create a new LastChangedEntry."""
        if entity_id in self.last_changed_entities:
            return False
        new_device = LastChangedEntry(**data, entity_id=entity_id)
        self.last_changed_entities[entity_id] = new_device
        self.async_schedule_save()
        return new_device

    @callback
    def async_delete_last_changed(self, entity_id: str) -> None:
        """Delete DeviceEntry."""
        if entity_id in self.last_changed_entities:
            del self.last_changed_entities[entity_id]
            self.async_schedule_save()
            return True
        return False

    @callback
    def async_update_last_changed(self, entity_id: str, changes: dict) -> LastChangedEntry:
        """Update existing DeviceEntry."""
        old = self.last_changed_entities[entity_id]
        new = self.last_changed_entities[entity_id] = attr.evolve(old, **changes)
        self.async_schedule_save()
        return new


@bind_hass
async def async_get_registry(hass: HomeAssistant) -> BatteryNotesStorage:
    """Return battery notes storage instance."""
    task = hass.data.get(DATA_REGISTRY)

    if task is None:

        async def _load_reg() -> BatteryNotesStorage:
            registry = BatteryNotesStorage(hass)
            await registry.async_load()
            return registry

        task = hass.data[DATA_REGISTRY] = hass.async_create_task(_load_reg())

    return cast(BatteryNotesStorage, await task)

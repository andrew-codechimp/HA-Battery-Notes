"""Data store for battery_notes."""
from __future__ import annotations

import json
import logging
import os
import attr
from typing import NamedTuple
from datetime import datetime, time, timedelta, timezone
from dataclasses import dataclass

from homeassistant.core import HomeAssistant
from homeassistant.config import get_default_config_dir
from homeassistant.helpers.storage import Store

from .const import (
    DOMAIN,
    DATA_LAST_CHANGED,
    DOMAIN_CONFIG,
    CONF_LAST_CHANGED_STORE,
)

_LOGGER = logging.getLogger(__name__)

DATA_REGISTRY = f"{DOMAIN}_storage"
STORAGE_KEY = f"{DOMAIN}.storage"
STORAGE_VERSION_MAJOR = 1
STORAGE_VERSION_MINOR = 0
SAVE_DELAY = 10


class MigratableStore(Store):
    """Hold last changed data."""

    @dataclass
    class DataStore:
        devices = {}

    _data_store = DataStore()

    _json_path: str = None

    def __init__(self, hass: HomeAssistant) -> None:
        """Init."""

        self._json_path = os.path.join(
            hass.config.config_dir,
            ".storage",
            CONF_LAST_CHANGED_STORE,
        )

        _LOGGER.debug("Using last changed store at %s", self._json_path)

        if os.path.exists(self._json_path):
            with open(self._json_path, encoding="utf-8") as myfile:
                json_data = json.load(myfile)
                self._data_store = json_data
                myfile.close()

            _LOGGER.debug("Loaded last changed store at %s", self._json_path)

    @staticmethod
    def factory(hass: HomeAssistant) -> LastChangedStore:
        """Return the library or create."""

        if DOMAIN not in hass.data:
            hass.data[DOMAIN] = {}

        if DATA_LAST_CHANGED in hass.data[DOMAIN]:
            return hass.data[DOMAIN][DATA_LAST_CHANGED]  # type: ignore

        last_changed_store = LastChangedStore(hass)
        hass.data[DOMAIN][DATA_LAST_CHANGED] = last_changed_store
        return last_changed_store

    async def get_device_battery_last_changed(self, device_id: str) -> datetime | None:
        """Return last changed date time."""

        if self._data_store.devices is not None:
            return self._data_store.devices[device_id]

        return None

    async def set_device_battery_last_changed(
        self, device_id: str, last_changed: datetime | None
    ) -> None:
        """Add or update the dictionary item."""

        if self._data_store:
            self._data_store.devices[device_id] = last_changed
        else:
            self._data_store.devices = {device_id: last_changed}

        print(self._data_store.devices)

        if self._data_store:
            json_str = json.dumps(
                self._data_store, ensure_ascii=False, indent=4, default=str
            )

            print(json_str)
        else:
            print("No devices")

        with open(self._json_path, "w", encoding="utf-8") as myfile:
            myfile.write(json_str)
            # json.dump(json_str,
            #           myfile,
            #           ensure_ascii=False,
            #           indent=4,
            #           default=str)
            myfile.close()

        return None

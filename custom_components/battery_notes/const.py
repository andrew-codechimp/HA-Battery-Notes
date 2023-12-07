"""Constants for battery_notes."""
import json
from logging import Logger, getLogger
from pathlib import Path
from typing import Final

from homeassistant.const import Platform

LOGGER: Logger = getLogger(__package__)

manifestfile = Path(__file__).parent / "manifest.json"
with open(file=manifestfile, encoding="UTF-8") as json_file:
    manifest_data = json.load(json_file)

DOMAIN = manifest_data.get("domain")
NAME = manifest_data.get("name")
VERSION = manifest_data.get("version")
ISSUEURL = manifest_data.get("issue_tracker")
MANUFACTURER = "@Andrew-CodeChimp"

DOMAIN_CONFIG = "config"

CONF_DEVICE_ID = "device_id"
CONF_BATTERY_TYPE = "battery_type"
CONF_SENSORS = "sensors"

DATA_CONFIGURED_ENTITIES = "configured_entities"

PLATFORMS: Final = [
    Platform.SENSOR,
]

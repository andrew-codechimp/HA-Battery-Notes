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

CONF_BATTERY_TYPE = "battery_type"
CONF_SENSORS = "sensors"
CONF_ENABLE_AUTODISCOVERY = "enable_autodiscovery"
CONF_LIBRARY = "library"
CONF_MODEL = "model"
CONF_MANUFACTURER = "manufacturer"
CONF_DEVICE_NAME = "device_name"
CONF_LIBRARY_URL = "https://raw.githubusercontent.com/andrew-codechimp/HA-Battery-Notes/main/custom_components/battery_notes/data/library.json"  # pylint: disable=line-too-long

DATA_CONFIGURED_ENTITIES = "configured_entities"
DATA_DISCOVERED_ENTITIES = "discovered_entities"
DATA_DOMAIN_ENTITIES = "domain_entities"
DATA_LIBRARY = "library"
DATA_UPDATE_COORDINATOR = "update_coordinator"
DATA_LIBRARY_LAST_UPDATE = "library_last_update"

PLATFORMS: Final = [
    Platform.SENSOR,
]

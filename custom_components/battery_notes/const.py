"""Constants for battery_notes."""
import json
from logging import Logger, getLogger
from pathlib import Path
from typing import Final
import voluptuous as vol

from homeassistant.const import Platform

from homeassistant.helpers import config_validation as cv

LOGGER: Logger = getLogger(__package__)

manifestfile = Path(__file__).parent / "manifest.json"
with open(file=manifestfile, encoding="UTF-8") as json_file:
    manifest_data = json.load(json_file)

DOMAIN = manifest_data.get("domain")
NAME = manifest_data.get("name")
VERSION = manifest_data.get("version")
ISSUEURL = manifest_data.get("issue_tracker")
MANUFACTURER = "@Andrew-CodeChimp"
LAST_REPLACED = "battery_last_replaced"

DOMAIN_CONFIG = "config"

CONF_BATTERY_TYPE = "battery_type"
CONF_SENSORS = "sensors"
CONF_ENABLE_AUTODISCOVERY = "enable_autodiscovery"
CONF_USER_LIBRARY = "user_library"
CONF_MODEL = "model"
CONF_MANUFACTURER = "manufacturer"
CONF_DEVICE_NAME = "device_name"
CONF_LIBRARY_URL = "https://raw.githubusercontent.com/andrew-codechimp/HA-Battery-Notes/main/custom_components/battery_notes/data/library.json"  # pylint: disable=line-too-long
CONF_SHOW_ALL_DEVICES = "show_all_devices"
CONF_ENABLE_REPLACED = "enable_replaced"

DATA_CONFIGURED_ENTITIES = "configured_entities"
DATA_DISCOVERED_ENTITIES = "discovered_entities"
DATA_DOMAIN_ENTITIES = "domain_entities"
DATA_LIBRARY = "library"
DATA_LIBRARY_UPDATER = "library_updater"
DATA_LIBRARY_LAST_UPDATE = "library_last_update"
DATA_COORDINATOR = "coordinator"
DATA_STORE = "store"

SERVICE_BATTERY_REPLACED = "set_battery_replaced"

ATTR_DEVICE_ID = "device_id"
ATTR_DATE_TIME_REPLACED = "datetime_replaced"
ATTR_REMOVE = "remove"
ATTR_BATTERY_QUANTITY = "battery_quantity"
ATTR_BATTERY_TYPE = "battery_type"


SERVICE_BATTERY_REPLACED_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_DATE_TIME_REPLACED): cv.datetime
    }
)

PLATFORMS: Final = [
    Platform.BUTTON,
    Platform.SENSOR,
]

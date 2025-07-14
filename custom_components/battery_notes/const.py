"""Constants for battery_notes."""

import json
from logging import Logger, getLogger
from pathlib import Path
from typing import Final

import voluptuous as vol
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

LOGGER: Logger = getLogger(__package__)

MIN_HA_VERSION = "2025.4.0"

manifestfile = Path(__file__).parent / "manifest.json"
with open(file=manifestfile, encoding="UTF-8") as json_file:
    manifest_data = json.load(json_file)

DOMAIN = manifest_data.get("domain")
NAME = manifest_data.get("name")
VERSION = manifest_data.get("version")
ISSUEURL = manifest_data.get("issue_tracker")
MANUFACTURER = "@Andrew-CodeChimp"
LAST_REPLACED = "battery_last_replaced"
LAST_REPORTED = "battery_last_reported"
LAST_REPORTED_LEVEL = "battery_last_reported_level"

DOMAIN_CONFIG = "config"

DEFAULT_BATTERY_LOW_THRESHOLD = 10
DEFAULT_BATTERY_INCREASE_THRESHOLD = 25
DEFAULT_LIBRARY_URL = "https://battery-notes-data.codechimp.org/library.json"
DEFAULT_SCHEMA_URL = "https://battery-notes-data.codechimp.org/schema.json"

CONF_SOURCE_ENTITY_ID = "source_entity_id"
CONF_BATTERY_TYPE = "battery_type"
CONF_BATTERY_QUANTITY = "battery_quantity"
CONF_BATTERY_LOW_THRESHOLD = "battery_low_threshold"
CONF_SENSORS = "sensors"
CONF_ENABLE_AUTODISCOVERY = "enable_autodiscovery"
CONF_USER_LIBRARY = "user_library"
CONF_MODEL = "model"
CONF_MODEL_ID = "model_id"
CONF_MANUFACTURER = "manufacturer"
CONF_DEVICE_NAME = "device_name"
CONF_LIBRARY_URL = "library_url"
CONF_SCHEMA_URL = "schema_url"
CONF_SHOW_ALL_DEVICES = "show_all_devices"
CONF_ENABLE_REPLACED = "enable_replaced"
CONF_DEFAULT_BATTERY_LOW_THRESHOLD = "default_battery_low_threshold"
CONF_BATTERY_INCREASE_THRESHOLD = "battery_increase_threshold"
CONF_HIDE_BATTERY = "hide_battery"
CONF_ROUND_BATTERY = "round_battery"
CONF_BATTERY_LOW_TEMPLATE = "battery_low_template"
CONF_FILTER_OUTLIERS = "filter_outliers"

DATA_CONFIGURED_ENTITIES = "configured_entities"
DATA_DISCOVERED_ENTITIES = "discovered_entities"
DATA_DOMAIN_ENTITIES = "domain_entities"
DATA_LIBRARY = "library"
DATA_LIBRARY_UPDATER = "library_updater"

SERVICE_BATTERY_REPLACED = "set_battery_replaced"
SERVICE_DATA_DATE_TIME_REPLACED = "datetime_replaced"

SERVICE_CHECK_BATTERY_LAST_REPORTED = "check_battery_last_reported"
SERVICE_DATA_DAYS_LAST_REPORTED = "days_last_reported"
SERVICE_CHECK_BATTERY_LOW = "check_battery_low"

EVENT_BATTERY_THRESHOLD = "battery_notes_battery_threshold"
EVENT_BATTERY_INCREASED = "battery_notes_battery_increased"
EVENT_BATTERY_NOT_REPORTED = "battery_notes_battery_not_reported"
EVENT_BATTERY_REPLACED = "battery_notes_battery_replaced"

ATTR_DEVICE_ID = "device_id"
ATTR_SOURCE_ENTITY_ID = "source_entity_id"
ATTR_REMOVE = "remove"
ATTR_BATTERY_QUANTITY = "battery_quantity"
ATTR_BATTERY_TYPE = "battery_type"
ATTR_BATTERY_TYPE_AND_QUANTITY = "battery_type_and_quantity"
ATTR_BATTERY_LAST_REPLACED = "battery_last_replaced"
ATTR_BATTERY_LOW = "battery_low"
ATTR_BATTERY_LOW_THRESHOLD = "battery_low_threshold"
ATTR_DEVICE_NAME = "device_name"
ATTR_BATTERY_LEVEL = "battery_level"
ATTR_BATTERY_LAST_REPORTED = "battery_last_reported"
ATTR_BATTERY_LAST_REPORTED_DAYS = "battery_last_reported_days"
ATTR_BATTERY_LAST_REPORTED_LEVEL = "battery_last_reported_level"
ATTR_PREVIOUS_BATTERY_LEVEL = "previous_battery_level"
ATTR_BATTERY_THRESHOLD_REMINDER = "reminder"

WINDOW_SIZE_UNIT_NUMBER_EVENTS = 1
WINDOW_SIZE_UNIT_TIME = 2

SERVICE_BATTERY_REPLACED_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DEVICE_ID): cv.string,
        vol.Optional(ATTR_SOURCE_ENTITY_ID): cv.string,
        vol.Optional(SERVICE_DATA_DATE_TIME_REPLACED): cv.datetime,
    }
)

SERVICE_CHECK_BATTERY_LAST_REPORTED_SCHEMA = vol.Schema(
    {
        vol.Required(SERVICE_DATA_DAYS_LAST_REPORTED): cv.positive_int,
    }
)

PLATFORMS: Final = [
    Platform.BUTTON,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

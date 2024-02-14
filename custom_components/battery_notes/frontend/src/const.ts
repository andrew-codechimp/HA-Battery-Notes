export const VERSION = "v2024.1.0";
export const REPO = "https://github.com/jeroenterheerdt/HASmartIrrigation;";
export const ISSUES_URL = REPO + "/issues";

export const PLATFORM = "smart-irrigation";
export const DOMAIN = "smart_irrigation";
export const editConfigService = "edit_config";

export const CONF_CALC_TIME = "calctime";
export const CONF_AUTO_CALC_ENABLED = "autocalcenabled";
export const CONF_AUTO_UPDATE_ENABLED = "autoupdateenabled";
export const CONF_AUTO_UPDATE_SCHEDULE = "autoupdateschedule";
export const CONF_AUTO_UPDATE_TIME = "autoupdatefirsttime";
export const CONF_AUTO_UPDATE_INTERVAL = "autoupdateinterval";
export const CONF_AUTO_CLEAR_ENABLED = "autoclearenabled";
export const CONF_CLEAR_TIME = "cleardatatime";

export const AUTO_UPDATE_SCHEDULE_MINUTELY = "minutes";
export const AUTO_UPDATE_SCHEDULE_HOURLY = "hours";
export const AUTO_UPDATE_SCHEDULE_DAILY = "days";
export const CONF_IMPERIAL = "imperial";
export const CONF_METRIC = "metric";

export const MAPPING_DEWPOINT = "Dewpoint";
export const MAPPING_EVAPOTRANSPIRATION = "Evapotranspiration";
export const MAPPING_HUMIDITY = "Humidity";
//removing this as part of beta12. Temperature is the only thing we want to take and we will apply min and max aggregation on our own.
//export const MAPPING_MAX_TEMP = "Maximum Temperature";
//export const MAPPING_MIN_TEMP = "Minimum Temperature";
export const MAPPING_PRECIPITATION = "Precipitation";
export const MAPPING_PRESSURE = "Pressure";
export const MAPPING_SOLRAD = "Solar Radiation";
export const MAPPING_TEMPERATURE = "Temperature";
export const MAPPING_WINDSPEED = "Windspeed";

export const MAPPING_CONF_SOURCE_OWM = "owm";
export const MAPPING_CONF_SOURCE_SENSOR = "sensor";
export const MAPPING_CONF_SOURCE_STATIC_VALUE = "static";
export const MAPPING_CONF_PRESSURE_TYPE = "pressure_type";
export const MAPPING_CONF_PRESSURE_ABSOLUTE = "absolute";
export const MAPPING_CONF_PRESSURE_RELATIVE = "relative";
export const MAPPING_CONF_SOURCE_NONE = "none";
export const MAPPING_CONF_SOURCE = "source";
export const MAPPING_CONF_SENSOR = "sensorentity";
export const MAPPING_CONF_STATIC_VALUE = "static_value";
export const MAPPING_CONF_UNIT = "unit";
export const MAPPING_DATA = "data";
export const MAPPING_CONF_AGGREGATE = "aggregate";
export const MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT = "average";
export const MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_PRECIPITATION = "maximum";
//removing this as part of beta12. Temperature is the only thing we want to take and we will apply min and max aggregation on our own.
//export const MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_MAX_TEMP = "maximum";
//export const MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_MIN_TEMP = "minimum";
export const MAPPING_CONF_AGGREGATE_OPTIONS = [
  "average",
  "first",
  "last",
  "maximum",
  "median",
  "minimum",
  "sum",
];

export const UNIT_M2 = "m<sup>2</sup>";
export const UNIT_SQ_FT = "sq ft";
export const UNIT_LPM = "l/minute";
export const UNIT_GPM = "gal/minute";
export const UNIT_SECONDS = "s";
export const UNIT_DEGREES_C = "°C";
export const UNIT_DEGREES_F = "°F";
export const UNIT_MM = "mm";
export const UNIT_INCH = "in";
export const UNIT_PERCENT = "%";
export const UNIT_MBAR = "millibar";
export const UNIT_HPA = "hPa";
export const UNIT_PSI = "psi";
export const UNIT_INHG = "inch Hg";
export const UNIT_KMH = "km/h";
export const UNIT_MH = "mile/h";
export const UNIT_MS = "meter/s";
export const UNIT_W_M2 = "W/m2";
export const UNIT_W_SQFT = "W/sq ft";
export const UNIT_MJ_DAY_M2 = "MJ/day/m2";
export const UNIT_MJ_DAY_SQFT = "MJ/day/sq ft";

export const ZONE_ID = "id";
export const ZONE_NAME = "name";
export const ZONE_SIZE = "size";
export const ZONE_THROUGHPUT = "throughput";
export const ZONE_STATE = "state";
export const ZONE_DURATION = "duration";
export const ZONE_STATE_DISABLED = "disabled";
export const ZONE_STATE_MANUAL = "manual";
export const ZONE_STATE_AUTOMATIC = "automatic";
export const ZONE_MODULE = "module";
export const ZONE_BUCKET = "bucket";
export const ZONE_OLD_BUCKET = "old_bucket";
export const ZONE_DELTA = "delta";
export const ZONE_EXPLANATION = "explanation";
export const ZONE_MULTIPLIER = "multiplier";
export const ZONE_MAPPING = "mapping";
export const ZONE_LEAD_TIME = "lead_time";
export const ZONE_MAXIMUM_DURATION = "maximum_duration";
export const ZONE_MAXIMUM_BUCKET = "maximum_bucket";

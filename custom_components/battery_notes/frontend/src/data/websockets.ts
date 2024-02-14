import { HomeAssistant } from "custom-card-helpers";
import {
  SmartIrrigationConfig,
  SmartIrrigationZone,
  SmartIrrigationModule,
  SmartIrrigationMapping,
} from "../types";
import { DOMAIN } from "../const";

export const fetchConfig = (
  hass: HomeAssistant
): Promise<SmartIrrigationConfig> =>
  hass.callWS({
    type: DOMAIN + "/config",
  });

export const saveConfig = (
  hass: HomeAssistant,
  config: Partial<SmartIrrigationConfig>
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/config", config);
};

/*export const fetchZones = (
  hass: HomeAssistant
): Promise<Dictionary<SmartIrrigationZone>> =>*/
export const fetchZones = (
  hass: HomeAssistant
): Promise<SmartIrrigationZone[]> =>
  hass.callWS({
    type: DOMAIN + "/zones",
  });

export const saveZone = (
  hass: HomeAssistant,
  config: Partial<SmartIrrigationZone>
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/zones", config);
};

export const calculateZone = (
  hass: HomeAssistant,
  zone_id: string
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/zones", {
    id: zone_id,
    calculate: true,
    override_cache: true,
  });
};

export const updateZone = (
  hass: HomeAssistant,
  zone_id: string
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/zones", {
    id: zone_id,
    update: true,
  });
};
export const calculateAllZones = (hass: HomeAssistant): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/zones", {
    calculate_all: true,
  });
};

export const updateAllZones = (hass: HomeAssistant): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/zones", {
    update_all: true,
  });
};

export const resetAllBuckets = (hass: HomeAssistant): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/zones", {
    reset_all_buckets: true,
  });
};

export const clearAllWeatherdata = (hass: HomeAssistant): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/zones", {
    clear_all_weatherdata: true,
  });
};


export const deleteZone = (
  hass: HomeAssistant,
  zone_id: string
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/zones", {
    id: zone_id,
    remove: true,
  });
};

export const fetchModules = (
  hass: HomeAssistant
): Promise<SmartIrrigationModule[]> =>
  hass.callWS({
    type: DOMAIN + "/modules",
  });

export const fetchAllModules = (
  hass: HomeAssistant
): Promise<SmartIrrigationModule[]> =>
  hass.callWS({
    type: DOMAIN + "/allmodules",
  });

export const saveModule = (
  hass: HomeAssistant,
  config: Partial<SmartIrrigationModule>
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/modules", config);
};

export const deleteModule = (
  hass: HomeAssistant,
  module_id: string
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/modules", {
    id: module_id,
    remove: true,
  });
};

export const fetchMappings = (
  hass: HomeAssistant
): Promise<SmartIrrigationMapping[]> =>
  hass.callWS({
    type: DOMAIN + "/mappings",
  });
export const saveMapping = (
  hass: HomeAssistant,
  config: Partial<SmartIrrigationMapping>
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/mappings", config);
};

export const deleteMapping = (
  hass: HomeAssistant,
  module_id: string
): Promise<boolean> => {
  return hass.callApi("POST", DOMAIN + "/mappings", {
    id: module_id,
    remove: true,
  });
};

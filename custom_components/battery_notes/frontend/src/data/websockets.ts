import { Dictionary, BatteryNotesDevice, HomeAssistant } from "../types";

export const fetchDevices = (
  hass: HomeAssistant,
): Promise<Dictionary<BatteryNotesDevice>> =>
  hass.callWS({
    type: "batterynotes/devices",
  });

export const saveDevice = (
  hass: HomeAssistant,
  config: Partial<BatteryNotesDevice> & { device_id: string },
): Promise<boolean> => {
  return hass.callApi("POST", "batterynotes/devices", config);
};

export const deleteDevice = (
  hass: HomeAssistant,
  device_id: string,
): Promise<boolean> => {
  return hass.callApi("POST", "batterynotes/devices", {
    device_id: device_id,
    remove: true,
  });
};

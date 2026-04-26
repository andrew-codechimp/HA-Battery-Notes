const WS_LIST_DEVICES = "battery_notes/list_devices";

export type BatteryDeviceRow = {
  subentry_id: string;
  device_name: string;
  battery_percentage: number | null;
};

type HassLike = {
  callWS: (msg: { type: string }) => Promise<unknown>;
};

export async function fetchBatteryDevices(hass: HassLike): Promise<BatteryDeviceRow[]> {
  const response = await hass.callWS({ type: WS_LIST_DEVICES });

  if (!Array.isArray(response)) {
    return [];
  }

  return response.map((row) => {
    const record = (row ?? {}) as Record<string, unknown>;

    return {
      subentry_id: String(record.subentry_id ?? ""),
      device_name: String(record.device_name ?? "Unknown device"),
      battery_percentage: parseBatteryPercentage(record.battery_percentage),
    };
  });
}

function parseBatteryPercentage(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isNaN(value) ? null : value;
  }

  if (typeof value === "string") {
    const parsed = Number.parseFloat(value);
    return Number.isNaN(parsed) ? null : parsed;
  }

  return null;
}

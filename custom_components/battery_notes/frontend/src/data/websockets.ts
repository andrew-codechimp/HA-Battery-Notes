const WS_LIST_DEVICES = "battery_notes/list_devices";

export type BatteryDeviceRow = {
  subentry_id: string;
  device_name: string;
  battery_type: string;
  battery_quantity: number | null;
  battery_percentage: number | null;
  battery_low: boolean;
  last_replaced: string | null;
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
      battery_type: String(record.battery_type ?? "-"),
      battery_quantity: parseBatteryQuantity(record.battery_quantity),
      battery_percentage: parseBatteryPercentage(record.battery_percentage),
      battery_low: parseBatteryLow(record.battery_low),
      last_replaced: parseLastReplaced(record.last_replaced),
    };
  });
}

function parseLastReplaced(value: unknown): string | null {
  if (typeof value === "string" && value.length > 0) {
    return value;
  }
  return null;
}

function parseBatteryLow(value: unknown): boolean {
  if (typeof value === "boolean") {
    return value;
  }

  if (typeof value === "string") {
    return value.toLowerCase() === "true";
  }

  return false;
}

function parseBatteryQuantity(value: unknown): number | null {
  if (value === null || value === undefined) {
    return null;
  }

  if (typeof value === "number") {
    return Number.isNaN(value) ? null : value;
  }

  if (typeof value === "string") {
    const parsed = Number.parseInt(value, 10);
    return Number.isNaN(parsed) ? null : parsed;
  }

  return null;
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

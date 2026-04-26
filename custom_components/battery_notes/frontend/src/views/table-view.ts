import type { BatteryDeviceRow } from "../data/websockets.js";

type HassLike = {
  callWS: (msg: { type: string }) => Promise<unknown>;
};

type HaDataTableElement = HTMLElement & {
  hass?: HassLike | null;
  columns?: Record<
    string,
    {
      title: string;
      type?: string;
      sortable?: boolean;
      valueColumn?: string;
    }
  >;
  data?: Array<Record<string, unknown>>;
  id?: string;
  autoHeight?: boolean;
};

class BatteryNotesTableView extends HTMLElement {
  private _hass: HassLike | null = null;

  private _rows: BatteryDeviceRow[] = [];

  private _isLoading = false;

  private _errorMessage: string | null = null;

  set hass(hass: HassLike | null) {
    this._hass = hass;
    this._render();
  }

  set rows(rows: BatteryDeviceRow[]) {
    this._rows = rows;
    this._render();
  }

  set isLoading(isLoading: boolean) {
    this._isLoading = isLoading;
    this._render();
  }

  set errorMessage(errorMessage: string | null) {
    this._errorMessage = errorMessage;
    this._render();
  }

  connectedCallback(): void {
    this._render();
  }

  private _render(): void {
    if (this._isLoading) {
      this.innerHTML = "<p style=\"margin: 0;\">Loading battery notes...</p>";
      return;
    }

    if (this._errorMessage) {
      this.innerHTML = `<p style=\"margin: 0; color: var(--error-color);\">Failed to load battery notes: ${this._escapeHtml(this._errorMessage)}</p>`;
      return;
    }

    if (this._rows.length === 0) {
      this.innerHTML = "<p style=\"margin: 0;\">No battery notes configured.</p>";
      return;
    }

    this.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100%;
          min-height: 0;
        }

        ha-data-table {
          width: 100%;
          height: 100%;
          --data-table-border-width: 0;
        }
      </style>
      <ha-data-table id="battery-notes-table"></ha-data-table>
    `;

    const table = this.querySelector("#battery-notes-table") as
      | HaDataTableElement
      | null;

    if (!table) {
      return;
    }

    table.hass = this._hass;
    table.id = "subentry_id";
    table.autoHeight = false;
    table.columns = {
      device_name: { title: "Device", sortable: true },
      battery_type: { title: "Battery Type", sortable: true },
      battery_quantity_display: {
        title: "Quantity",
        type: "numeric",
        sortable: true,
        valueColumn: "battery_quantity_sort",
      },
      battery_display: {
        title: "Battery",
        type: "numeric",
        sortable: true,
        valueColumn: "battery_sort",
      },
    };
    table.data = this._rows.map((row) => ({
      subentry_id: row.subentry_id,
      device_name: row.device_name,
      battery_type: row.battery_type,
      battery_quantity_display: this._formatQuantity(row.battery_quantity),
      battery_quantity_sort: this._sortValue(row.battery_quantity),
      battery_display: this._formatBattery(row.battery_percentage),
      battery_sort: this._sortValue(row.battery_percentage),
    }));
  }

  private _sortValue(value: number | null): number {
    if (value === null || Number.isNaN(value)) {
      return 101;
    }

    return value;
  }

  private _formatBattery(value: number | null): string {
    if (value === null || Number.isNaN(value)) {
      return "-";
    }

    return `${Math.round(value)}%`;
  }

  private _formatQuantity(value: number | null): string {
    if (value === null || Number.isNaN(value)) {
      return "-";
    }

    return String(value);
  }

  private _escapeHtml(value: string): string {
    return value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
}

if (!customElements.get("battery-notes-table-view")) {
  customElements.define("battery-notes-table-view", BatteryNotesTableView);
}

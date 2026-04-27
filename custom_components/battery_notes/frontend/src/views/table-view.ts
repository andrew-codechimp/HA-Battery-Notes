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
      direction?: "asc" | "desc";
      valueColumn?: string;
      flex?: number;
    }
  >;
  data?: Array<Record<string, unknown>>;
  id?: string;
  autoHeight?: boolean;
  selectable?: boolean;
  selectAll?: () => void;
  clearSelection?: () => void;
};

type SelectionChangedDetail = {
  value?: string[];
};

class BatteryNotesTableView extends HTMLElement {
  private _hass: HassLike | null = null;

  private _rows: BatteryDeviceRow[] = [];

  private _isLoading = false;

  private _errorMessage: string | null = null;

  private _selectionMode = false;

  private _renderQueued = false;

  private _currentView: "loading" | "error" | "empty" | "table" | null = null;

  set hass(hass: HassLike | null) {
    this._hass = hass;
    this._queueRender();
  }

  set rows(rows: BatteryDeviceRow[]) {
    this._rows = rows;
    this._queueRender();
  }

  set isLoading(isLoading: boolean) {
    this._isLoading = isLoading;
    this._queueRender();
  }

  set errorMessage(errorMessage: string | null) {
    this._errorMessage = errorMessage;
    this._queueRender();
  }

  set selectionMode(selectionMode: boolean) {
    this._selectionMode = selectionMode;
    this._queueRender();
  }

  connectedCallback(): void {
    this._queueRender();
  }

  public selectAllRows(): void {
    const table = this.querySelector("#battery-notes-table") as
      | HaDataTableElement
      | null;
    table?.selectAll?.();
  }

  public clearSelectedRows(): void {
    const table = this.querySelector("#battery-notes-table") as
      | HaDataTableElement
      | null;
    table?.clearSelection?.();
  }

  private _queueRender(): void {
    if (this._renderQueued) {
      return;
    }

    this._renderQueued = true;
    queueMicrotask(() => {
      this._renderQueued = false;
      this._render();
    });
  }

  private _render(): void {
    const nextView = this._getView();

    if (this._currentView !== nextView) {
      this._currentView = nextView;

      if (nextView === "loading") {
        this.innerHTML = "<p style=\"margin: 0;\">Loading battery notes...</p>";
        return;
      }

      if (nextView === "error") {
        this.innerHTML = `<p style="margin: 0; color: var(--error-color);">Failed to load battery notes: ${this._escapeHtml(this._errorMessage ?? "Unknown error")}</p>`;
        return;
      }

      if (nextView === "empty") {
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
      table?.addEventListener("selection-changed", this._handleSelectionChanged);
    }

    if (nextView !== "table") {
      return;
    }

    const table = this.querySelector("#battery-notes-table") as
      | HaDataTableElement
      | null;

    if (!table) {
      return;
    }

    table.hass = this._hass;
    table.id = "subentry_id";
    table.autoHeight = false;
    table.selectable = this._selectionMode;
    table.columns = {
      device_name: { title: "Device", sortable: true, flex: 4 },
      battery_type: { title: "Battery Type", sortable: true, flex: 1 },
      battery_quantity_display: {
        title: "Quantity",
        type: "numeric",
        sortable: true,
        valueColumn: "battery_quantity_sort",
        flex: 1,
      },
      battery_display: {
        title: "Battery",
        type: "numeric",
        sortable: true,
        valueColumn: "battery_sort",
        flex: 1,
      },
      battery_low_display: {
        title: "Low",
        sortable: true,
        direction: "desc",
        valueColumn: "battery_low_sort",
        flex: 1,
      },
    };
    table.data = this._rows.map((row) => ({
      subentry_id: row.subentry_id,
      device_name: row.device_name,
      battery_low_display: this._formatBatteryLow(row.battery_low),
      battery_low_sort: row.battery_low ? 1 : 0,
      battery_type: row.battery_type,
      battery_quantity_display: this._formatQuantity(row.battery_quantity),
      battery_quantity_sort: this._sortValue(row.battery_quantity),
      battery_display: this._formatBattery(row.battery_percentage),
      battery_sort: this._sortValue(row.battery_percentage),
    }));
  }

  private _getView(): "loading" | "error" | "empty" | "table" {
    if (this._isLoading) {
      return "loading";
    }

    if (this._errorMessage) {
      return "error";
    }

    if (this._rows.length === 0) {
      return "empty";
    }

    return "table";
  }

  private _handleSelectionChanged = (event: Event): void => {
    const detail = (event as CustomEvent<SelectionChangedDetail>).detail;
    const selectedIds = Array.isArray(detail?.value) ? detail.value : [];

    this.dispatchEvent(
      new CustomEvent<string[]>("battery-notes-selection-changed", {
        detail: selectedIds,
        bubbles: true,
        composed: true,
      })
    );
  };

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

  private _formatBatteryLow(value: boolean): string {
    return value ? "Yes" : "No";
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

import type { BatteryDeviceRow } from "./data/websockets.js";
import { fetchBatteryDevices } from "./data/websockets.js";
import "./views/header-view";
import "./views/table-view";

type HassLike = {
  callWS: (msg: { type: string }) => Promise<unknown>;
};

type BatteryNotesTableViewElement = HTMLElement & {
  hass?: HassLike | null;
  rows?: BatteryDeviceRow[];
  isLoading?: boolean;
  errorMessage?: string | null;
};

type BatteryNotesHeaderViewElement = HTMLElement & {
  hass?: HassLike | null;
  narrow?: boolean;
};

const ROW_REFRESH_INTERVAL_MS = 15000;

class BatteryNotesPanel extends HTMLElement {
  private _hass: HassLike | null = null;

  private _narrow = false;

  private _rows: BatteryDeviceRow[] = [];

  private _isLoading = false;

  private _errorMessage: string | null = null;

  private _searchText = "";

  private _refreshIntervalId: number | null = null;

  private _isRefreshing = false;

  private _rowsSignature = "";

  set hass(hass: HassLike) {
    const firstSet = this._hass === null;
    this._hass = hass;

    if (firstSet) {
      this._render();
      void this._refreshRows(true);
    } else {
      this._syncHeaderViewState();
    }

    this._startAutoRefresh();
  }

  set narrow(narrow: boolean) {
    this._narrow = narrow;
    this._syncHeaderViewState();
  }

  connectedCallback(): void {
    document.addEventListener("visibilitychange", this._handleVisibilityChange);

    this._startAutoRefresh();
    if (!this.querySelector(".panel")) {
      this._render();
    }
  }

  disconnectedCallback(): void {
    document.removeEventListener(
      "visibilitychange",
      this._handleVisibilityChange
    );

    this._stopAutoRefresh();
  }

  private _startAutoRefresh(): void {
    if (!this.isConnected || !this._hass || this._refreshIntervalId !== null) {
      return;
    }

    this._refreshIntervalId = window.setInterval(() => {
      void this._refreshRows();
    }, ROW_REFRESH_INTERVAL_MS);
  }

  private _stopAutoRefresh(): void {
    if (this._refreshIntervalId === null) {
      return;
    }

    window.clearInterval(this._refreshIntervalId);
    this._refreshIntervalId = null;
  }

  private async _refreshRows(showLoading = false): Promise<void> {
    if (!this._hass || this._isRefreshing) {
      return;
    }

    this._isRefreshing = true;

    if (showLoading) {
      this._isLoading = true;
      this._render();
    }

    try {
      const fetchedRows = await fetchBatteryDevices(this._hass);
      const nextSignature = this._buildRowsSignature(fetchedRows);
      const rowsChanged = nextSignature !== this._rowsSignature;
      const errorChanged = this._errorMessage !== null;

      if (rowsChanged) {
        this._rows = fetchedRows;
        this._rowsSignature = nextSignature;
      }

      this._errorMessage = null;

      if (!showLoading && (rowsChanged || errorChanged)) {
        this._syncSearchInputState();
        this._syncTableViewState();
      }
    } catch (error) {
      const nextError =
        error instanceof Error ? error.message : "Unknown websocket error";
      const errorChanged = this._errorMessage !== nextError;
      this._errorMessage = nextError;

      if (!showLoading && errorChanged) {
        this._syncTableViewState();
      }
    } finally {
      this._isRefreshing = false;

      if (showLoading) {
        this._isLoading = false;
        this._render();
      }
    }
  }

  private _render(): void {
    this.innerHTML = `
      <style>
        :host {
          display: block;
          height: 100%;
          min-height: 0;
        }

        .panel {
          display: flex;
          flex-direction: column;
          height: 100%;
          min-height: 0;
        }

        .content {
          flex: 1;
          min-height: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 12px;
          overflow: hidden;
        }

        battery-notes-table-view {
          flex: 1;
          min-height: 0;
          display: block;
        }

        .table-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          padding: 12px 16px 0;
        }

        .table-title {
          margin: 0;
          font-size: 18px;
          font-weight: 500;
        }

        .search-input {
          flex: 1;
          min-width: 0;
          width: auto;
          box-sizing: border-box;
          padding: 8px 12px;
          border: 1px solid var(--divider-color);
          border-radius: 10px;
          background: var(--card-background-color);
          color: var(--primary-text-color);
          font: inherit;
        }

        .search-input::placeholder {
          color: var(--secondary-text-color);
        }

        .header-actions {
          display: flex;
          flex: 1;
          min-width: 0;
          align-items: center;
          gap: 12px;
        }
      </style>
      <div class="panel">
        <battery-notes-header-view class="main-header"></battery-notes-header-view>
        <div class="content">
          <div class="table-header">
            <div class="header-actions">
              <input
                class="search-input"
                type="search"
                placeholder="Search 0 devices"
              />
            </div>
          </div>
          <battery-notes-table-view></battery-notes-table-view>
        </div>
      </div>
    `;

    this._syncHeaderViewState();
    this._syncSearchInputState();
    this._syncTableViewState();
  }

  private _syncSearchInputState(): void {
    const input = this.querySelector(".search-input") as HTMLInputElement | null;
    if (!input) {
      return;
    }

    input.placeholder = `Search ${this._rows.length} devices`;
    input.value = this._searchText;
    input.addEventListener("input", this._handleSearchInput);
  }

  private _syncHeaderViewState(): void {
    const headerView = this.querySelector("battery-notes-header-view") as
      | BatteryNotesHeaderViewElement
      | null;

    if (!headerView) {
      return;
    }

    headerView.hass = this._hass;
    headerView.narrow = this._narrow;
  }

  private _syncTableViewState(): void {
    const tableView = this.querySelector("battery-notes-table-view") as
      | BatteryNotesTableViewElement
      | null;

    if (!tableView) {
      return;
    }

    tableView.hass = this._hass;
    tableView.rows = this._filterRows(this._rows);
    tableView.isLoading = this._isLoading;
    tableView.errorMessage = this._errorMessage;
  }

  private _handleSearchInput = (event: Event): void => {
    const input = event.currentTarget as HTMLInputElement;
    this._searchText = input.value;
    this._syncTableViewState();
  };

  private _handleVisibilityChange = (): void => {
    if (document.visibilityState !== "visible") {
      return;
    }

    void this._refreshRows();
  };

  private _filterRows(rows: BatteryDeviceRow[]): BatteryDeviceRow[] {
    const search = this._searchText.trim().toLowerCase();
    if (!search) {
      return rows;
    }

    return rows.filter((row) => {
      const deviceName = row.device_name.toLowerCase();
      const batteryType = row.battery_type.toLowerCase();
      const area = (row.area ?? "").toLowerCase();
      const floor = (row.floor ?? "").toLowerCase();
      const lastReplaced = row.last_replaced
        ? new Date(row.last_replaced).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          }).toLowerCase()
        : "";
      return (
        deviceName.includes(search) ||
        batteryType.includes(search) ||
        area.includes(search) ||
        floor.includes(search) ||
        lastReplaced.includes(search)
      );
    });
  }

  private _buildRowsSignature(rows: BatteryDeviceRow[]): string {
    return rows
      .map((row) =>
        [
          row.subentry_id,
          row.device_name,
          row.area ?? "",
          row.floor ?? "",
          row.last_replaced ?? "",
          row.battery_type,
          row.battery_quantity ?? "",
          row.battery_percentage ?? "",
          row.battery_low ? "1" : "0",
        ].join("|")
      )
      .join("\n");
  }
}

if (!customElements.get("battery-notes-panel")) {
  customElements.define("battery-notes-panel", BatteryNotesPanel);
}

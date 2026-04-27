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
  selectionMode?: boolean;
  selectAllRows?: () => void;
  clearSelectedRows?: () => void;
};

type BatteryNotesHeaderViewElement = HTMLElement & {
  hass?: HassLike | null;
  narrow?: boolean;
};

class BatteryNotesPanel extends HTMLElement {
  private _hass: HassLike | null = null;

  private _narrow = false;

  private _rows: BatteryDeviceRow[] = [];

  private _isLoading = false;

  private _errorMessage: string | null = null;

  private _searchText = "";

  private _selectionMode = false;

  private _selectedIds: string[] = [];

  set hass(hass: HassLike) {
    const firstSet = this._hass === null;
    this._hass = hass;

    if (firstSet) {
      void this._loadRows();
    }

    this._render();
  }

  set narrow(narrow: boolean) {
    this._narrow = narrow;
    this._syncHeaderViewState();
  }

  connectedCallback(): void {
    this.addEventListener(
      "battery-notes-selection-changed",
      this._handleSelectionChanged as EventListener
    );
    this._render();
  }

  disconnectedCallback(): void {
    this.removeEventListener(
      "battery-notes-selection-changed",
      this._handleSelectionChanged as EventListener
    );
  }

  private async _loadRows(): Promise<void> {
    if (!this._hass) {
      return;
    }

    this._isLoading = true;
    this._render();

    try {
      this._rows = await fetchBatteryDevices(this._hass);
      this._errorMessage = null;
    } catch (error) {
      this._errorMessage =
        error instanceof Error ? error.message : "Unknown websocket error";
    } finally {
      this._isLoading = false;
      this._render();
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
          padding: 0 16px 16px;
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
          padding-top: 12px;
        }

        .table-title {
          margin: 0;
          font-size: 18px;
          font-weight: 500;
        }

        .search-input {
          width: min(360px, 100%);
          max-width: 100%;
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
          align-items: center;
          gap: 12px;
        }

        .selection-mode-button {
          min-width: 96px;
        }

        .selection-mode-button-icon {
          margin-right: 8px;
          vertical-align: text-bottom;
        }

        .selection-mode-button.hidden {
          display: none;
        }

        .main-header.hidden {
          display: none;
        }

        .selection-header {
          display: flex;
          align-items: center;
          gap: 8px;
          min-height: var(--header-height);
          padding: 0 16px;
          background-color: var(--app-header-background-color);
          color: var(--app-header-text-color, white);
          border-bottom: var(--app-header-border-bottom, none);
        }

        .selection-header.hidden {
          display: none;
        }

        .selection-header-title {
          margin: 0;
          font-size: 20px;
          font-weight: 400;
          line-height: 20px;
        }

        .selection-close {
          color: var(--app-header-text-color, white);
          min-width: 40px;
          width: 40px;
          height: 40px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }
      </style>
      <div class="panel">
        <battery-notes-header-view class="main-header"></battery-notes-header-view>
        <div class="selection-header hidden">
          <ha-button class="selection-close" appearance="plain" title="Exit selection mode" aria-label="Exit selection mode">
            <ha-icon icon="mdi:close"></ha-icon>
          </ha-button>
          <p class="selection-header-title">0 selected</p>
        </div>
        <div class="content">
          <div class="table-header">
            <div class="header-actions">
              <ha-button class="selection-mode-button" appearance="plain">
                <ha-icon class="selection-mode-button-icon" icon="mdi:format-list-checks"></ha-icon>
              </ha-button>
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
    this._syncSelectionActionState();
    this._syncSelectionHeaderState();
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

  private _syncSelectionActionState(): void {
    const selectButton = this.querySelector(".selection-mode-button") as
      | HTMLElement
      | null;
    if (!selectButton) {
      return;
    }

    selectButton.addEventListener("click", this._handleSelectionModeStart);
  }

  private _syncSelectionHeaderState(): void {
    const header = this.querySelector(".selection-header") as HTMLElement | null;
    const title = this.querySelector(".selection-header-title") as
      | HTMLElement
      | null;
    const close = this.querySelector(".selection-close") as HTMLElement | null;
    const mainHeader = this.querySelector(".main-header") as HTMLElement | null;
    if (!header || !title || !close || !mainHeader) {
      return;
    }

    const selectButton = this.querySelector(".selection-mode-button") as
      | HTMLElement
      | null;

    if (!this._selectionMode) {
      header.classList.add("hidden");
      mainHeader.classList.remove("hidden");
      selectButton?.classList.remove("hidden");
      return;
    }

    header.classList.remove("hidden");
    mainHeader.classList.add("hidden");
    selectButton?.classList.add("hidden");
    const selectedCount = this._selectedIds.length;
    title.textContent = `${selectedCount} selected`;
    (close as HTMLButtonElement).onclick = this._handleSelectionModeExit;
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
    tableView.selectionMode = this._selectionMode;
  }

  private _handleSearchInput = (event: Event): void => {
    const input = event.currentTarget as HTMLInputElement;
    this._searchText = input.value;
    this._syncTableViewState();
  };

  private _handleSelectionModeStart = (): void => {
    this._selectionMode = true;
    this._syncSelectionHeaderState();
    this._syncTableViewState();
  };

  private _handleSelectionModeExit = (): void => {
    this._selectionMode = false;
    this._selectedIds = [];
    this._syncTableViewState();
    this._syncSelectionHeaderState();
  };

  private _handleSelectionChanged = (event: Event): void => {
    const selectedIds = (event as CustomEvent<string[]>).detail;
    this._selectedIds = Array.isArray(selectedIds) ? selectedIds : [];
    this._syncSelectionHeaderState();
  };

  private _filterRows(rows: BatteryDeviceRow[]): BatteryDeviceRow[] {
    const search = this._searchText.trim().toLowerCase();
    if (!search) {
      return rows;
    }

    return rows.filter((row) => {
      const deviceName = row.device_name.toLowerCase();
      const batteryType = row.battery_type.toLowerCase();
      return deviceName.includes(search) || batteryType.includes(search);
    });
  }
}

if (!customElements.get("battery-notes-panel")) {
  customElements.define("battery-notes-panel", BatteryNotesPanel);
}

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

class BatteryNotesPanel extends HTMLElement {
  private _hass: HassLike | null = null;

  private _narrow = false;

  private _rows: BatteryDeviceRow[] = [];

  private _isLoading = false;

  private _errorMessage: string | null = null;

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
    this._render();
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
        }
      </style>
      <div class="panel">
        <battery-notes-header-view></battery-notes-header-view>
        <div class="content">
          <battery-notes-table-view></battery-notes-table-view>
        </div>
      </div>
    `;

    this._syncHeaderViewState();
    this._syncTableViewState();
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
    tableView.rows = this._rows;
    tableView.isLoading = this._isLoading;
    tableView.errorMessage = this._errorMessage;
  }
}

if (!customElements.get("battery-notes-panel")) {
  customElements.define("battery-notes-panel", BatteryNotesPanel);
}

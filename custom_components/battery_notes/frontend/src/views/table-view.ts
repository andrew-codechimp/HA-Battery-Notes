import type { BatteryDeviceRow } from "../data/websockets.js";

class BatteryNotesTableView extends HTMLElement {
  private _rows: BatteryDeviceRow[] = [];

  private _isLoading = false;

  private _errorMessage: string | null = null;

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
      <table style="width: 100%; border-collapse: collapse; background: var(--card-background-color); border-radius: 8px; overflow: hidden;">
        <thead>
          <tr>
            <th style="text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--divider-color);">Device</th>
            <th style="text-align: right; padding: 10px 12px; border-bottom: 1px solid var(--divider-color);">Battery</th>
          </tr>
        </thead>
        <tbody>
          ${this._rows
            .map(
              (row) => `
                <tr>
                  <td style="padding: 10px 12px; border-bottom: 1px solid var(--divider-color);">${this._escapeHtml(row.device_name)}</td>
                  <td style="padding: 10px 12px; border-bottom: 1px solid var(--divider-color); text-align: right;">${this._formatBattery(row.battery_percentage)}</td>
                </tr>
              `
            )
            .join("")}
        </tbody>
      </table>
    `;
  }

  private _formatBattery(value: number | null): string {
    if (value === null || Number.isNaN(value)) {
      return "-";
    }

    return `${Math.round(value)}%`;
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

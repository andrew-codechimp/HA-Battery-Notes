import { BatteryDeviceRow, fetchBatteryDevices } from "./data/websockets";

type HassLike = {
  callWS: (msg: { type: string }) => Promise<unknown>;
};

class BatteryNotesPanel extends HTMLElement {
  private _hass: HassLike | null = null;

  private _rows: BatteryDeviceRow[] = [];

  private _isLoading = false;

  private _errorMessage: string | null = null;

  set hass(hass: HassLike) {
    const firstSet = this._hass === null;
    this._hass = hass;

    if (firstSet) {
      void this._loadRows();
    }
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
    const body = this._isLoading
      ? "<p style=\"margin: 0;\">Loading battery notes...</p>"
      : this._errorMessage
        ? `<p style=\"margin: 0; color: var(--error-color);\">Failed to load battery notes: ${this._escapeHtml(this._errorMessage)}</p>`
        : this._rows.length === 0
          ? "<p style=\"margin: 0;\">No battery notes configured.</p>"
          : `
            <table style=\"width: 100%; border-collapse: collapse; background: var(--card-background-color); border-radius: 8px; overflow: hidden;\">
              <thead>
                <tr>
                  <th style=\"text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--divider-color);\">Device</th>
                  <th style=\"text-align: right; padding: 10px 12px; border-bottom: 1px solid var(--divider-color);\">Battery</th>
                </tr>
              </thead>
              <tbody>
                ${this._rows
                  .map(
                    (row) => `
                      <tr>
                        <td style=\"padding: 10px 12px; border-bottom: 1px solid var(--divider-color);\">${this._escapeHtml(row.device_name)}</td>
                        <td style=\"padding: 10px 12px; border-bottom: 1px solid var(--divider-color); text-align: right;\">${this._formatBattery(row.battery_percentage)}</td>
                      </tr>
                    `
                  )
                  .join("")}
              </tbody>
            </table>
          `;

    this.innerHTML = `
      <div style="padding: 24px; max-width: 800px; margin: 0 auto;">
        <h1 style="margin: 0 0 8px 0;">Battery Notes</h1>
        <p style="margin: 0 0 16px 0; opacity: 0.8;">Configured battery note devices</p>
        ${body}
      </div>
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

if (!customElements.get("battery-notes-panel")) {
  customElements.define("battery-notes-panel", BatteryNotesPanel);
}

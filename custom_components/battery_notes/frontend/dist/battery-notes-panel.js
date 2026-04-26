const WS_LIST_DEVICES = "battery_notes/list_devices";
async function fetchBatteryDevices(hass) {
    const response = await hass.callWS({ type: WS_LIST_DEVICES });
    if (!Array.isArray(response)) {
        return [];
    }
    return response.map((row) => {
        const record = (row ?? {});
        return {
            subentry_id: String(record.subentry_id ?? ""),
            device_name: String(record.device_name ?? "Unknown device"),
            battery_type: String(record.battery_type ?? "-"),
            battery_quantity: parseBatteryQuantity(record.battery_quantity),
            battery_percentage: parseBatteryPercentage(record.battery_percentage),
        };
    });
}
function parseBatteryQuantity(value) {
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
function parseBatteryPercentage(value) {
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

class BatteryNotesHeaderView extends HTMLElement {
    _hass = null;
    _narrow = false;
    set hass(hass) {
        this._hass = hass;
        this._syncMenuButton();
    }
    set narrow(narrow) {
        this._narrow = narrow;
        this._syncMenuButton();
    }
    connectedCallback() {
        this._render();
    }
    _render() {
        this.innerHTML = `
      <style>
        .header {
          background-color: var(--app-header-background-color);
          color: var(--app-header-text-color, white);
          border-bottom: var(--app-header-border-bottom, none);
        }

        .toolbar {
          height: var(--header-height);
          display: flex;
          align-items: center;
          box-sizing: border-box;
          padding: 0 16px;
          font-size: 20px;
          font-weight: 400;
        }

        .main-title {
          margin: 0 0 0 24px;
          line-height: 20px;
          flex-grow: 1;
        }
      </style>
      <div class="header">
        <div class="toolbar">
          <ha-menu-button class="menu-button"></ha-menu-button>
          <div class="main-title">Battery Notes</div>
        </div>
      </div>
    `;
        this._syncMenuButton();
    }
    _syncMenuButton() {
        const menuButton = this.querySelector("ha-menu-button");
        if (!menuButton) {
            return;
        }
        if (this._hass) {
            menuButton.hass = this._hass;
        }
        menuButton.narrow = this._narrow;
    }
}
if (!customElements.get("battery-notes-header-view")) {
    customElements.define("battery-notes-header-view", BatteryNotesHeaderView);
}

class BatteryNotesTableView extends HTMLElement {
    _hass = null;
    _rows = [];
    _isLoading = false;
    _errorMessage = null;
    set hass(hass) {
        this._hass = hass;
        this._render();
    }
    set rows(rows) {
        this._rows = rows;
        this._render();
    }
    set isLoading(isLoading) {
        this._isLoading = isLoading;
        this._render();
    }
    set errorMessage(errorMessage) {
        this._errorMessage = errorMessage;
        this._render();
    }
    connectedCallback() {
        this._render();
    }
    _render() {
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
        const table = this.querySelector("#battery-notes-table");
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
    _sortValue(value) {
        if (value === null || Number.isNaN(value)) {
            return 101;
        }
        return value;
    }
    _formatBattery(value) {
        if (value === null || Number.isNaN(value)) {
            return "-";
        }
        return `${Math.round(value)}%`;
    }
    _formatQuantity(value) {
        if (value === null || Number.isNaN(value)) {
            return "-";
        }
        return String(value);
    }
    _escapeHtml(value) {
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

class BatteryNotesPanel extends HTMLElement {
    _hass = null;
    _narrow = false;
    _rows = [];
    _isLoading = false;
    _errorMessage = null;
    set hass(hass) {
        const firstSet = this._hass === null;
        this._hass = hass;
        if (firstSet) {
            void this._loadRows();
        }
        this._render();
    }
    set narrow(narrow) {
        this._narrow = narrow;
        this._syncHeaderViewState();
    }
    connectedCallback() {
        this._render();
    }
    async _loadRows() {
        if (!this._hass) {
            return;
        }
        this._isLoading = true;
        this._render();
        try {
            this._rows = await fetchBatteryDevices(this._hass);
            this._errorMessage = null;
        }
        catch (error) {
            this._errorMessage =
                error instanceof Error ? error.message : "Unknown websocket error";
        }
        finally {
            this._isLoading = false;
            this._render();
        }
    }
    _render() {
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
    _syncHeaderViewState() {
        const headerView = this.querySelector("battery-notes-header-view");
        if (!headerView) {
            return;
        }
        headerView.hass = this._hass;
        headerView.narrow = this._narrow;
    }
    _syncTableViewState() {
        const tableView = this.querySelector("battery-notes-table-view");
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

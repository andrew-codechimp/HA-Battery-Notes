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
            area: typeof record.area === "string" ? record.area : null,
            floor: typeof record.floor === "string" ? record.floor : null,
            battery_type: String(record.battery_type ?? "-"),
            battery_quantity: parseBatteryQuantity(record.battery_quantity),
            battery_percentage: parseBatteryPercentage(record.battery_percentage),
            battery_low: parseBatteryLow(record.battery_low),
            last_replaced: parseLastReplaced(record.last_replaced),
        };
    });
}
function parseLastReplaced(value) {
    if (typeof value === "string" && value.length > 0) {
        return value;
    }
    return null;
}
function parseBatteryLow(value) {
    if (typeof value === "boolean") {
        return value;
    }
    if (typeof value === "string") {
        return value.toLowerCase() === "true";
    }
    return false;
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
    _renderQueued = false;
    _currentView = null;
    set hass(hass) {
        this._hass = hass;
        this._queueRender();
    }
    set rows(rows) {
        this._rows = rows;
        this._queueRender();
    }
    set isLoading(isLoading) {
        this._isLoading = isLoading;
        this._queueRender();
    }
    set errorMessage(errorMessage) {
        this._errorMessage = errorMessage;
        this._queueRender();
    }
    connectedCallback() {
        this._queueRender();
    }
    _queueRender() {
        if (this._renderQueued) {
            return;
        }
        this._renderQueued = true;
        queueMicrotask(() => {
            this._renderQueued = false;
            this._render();
        });
    }
    _render() {
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
            this.querySelector("#battery-notes-table");
        }
        if (nextView !== "table") {
            return;
        }
        const table = this.querySelector("#battery-notes-table");
        if (!table) {
            return;
        }
        table.hass = this._hass;
        table.id = "subentry_id";
        table.autoHeight = false;
        table.columns = {
            device_name: { title: "Device", sortable: true, flex: 4 },
            area: { title: "Area", sortable: true, flex: 2 },
            floor: { title: "Floor", sortable: true, flex: 2 },
            last_replaced_display: {
                title: "Last Replaced",
                sortable: true,
                valueColumn: "last_replaced_sort",
                flex: 2,
            },
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
            area: row.area ?? "-",
            floor: row.floor ?? "-",
            last_replaced_display: this._formatDate(row.last_replaced),
            last_replaced_sort: row.last_replaced ?? "",
            battery_low_display: this._formatBatteryLow(row.battery_low),
            battery_low_sort: row.battery_low ? 1 : 0,
            battery_type: row.battery_type,
            battery_quantity_display: this._formatQuantity(row.battery_quantity),
            battery_quantity_sort: this._sortValue(row.battery_quantity),
            battery_display: this._formatBattery(row.battery_percentage),
            battery_sort: this._sortValue(row.battery_percentage),
        }));
    }
    _getView() {
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
    _formatDate(value) {
        if (!value) {
            return "-";
        }
        try {
            return new Date(value).toLocaleDateString(undefined, {
                year: "numeric",
                month: "short",
                day: "numeric",
            });
        }
        catch {
            return "-";
        }
    }
    _formatBatteryLow(value) {
        return value ? "Yes" : "No";
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

const ROW_REFRESH_INTERVAL_MS = 15000;
class BatteryNotesPanel extends HTMLElement {
    _hass = null;
    _narrow = false;
    _rows = [];
    _isLoading = false;
    _errorMessage = null;
    _searchText = "";
    _refreshIntervalId = null;
    _isRefreshing = false;
    _rowsSignature = "";
    set hass(hass) {
        const firstSet = this._hass === null;
        this._hass = hass;
        if (firstSet) {
            this._render();
            void this._refreshRows(true);
        }
        else {
            this._syncHeaderViewState();
        }
        this._startAutoRefresh();
    }
    set narrow(narrow) {
        this._narrow = narrow;
        this._syncHeaderViewState();
    }
    connectedCallback() {
        document.addEventListener("visibilitychange", this._handleVisibilityChange);
        this._startAutoRefresh();
        if (!this.querySelector(".panel")) {
            this._render();
        }
    }
    disconnectedCallback() {
        document.removeEventListener("visibilitychange", this._handleVisibilityChange);
        this._stopAutoRefresh();
    }
    _startAutoRefresh() {
        if (!this.isConnected || !this._hass || this._refreshIntervalId !== null) {
            return;
        }
        this._refreshIntervalId = window.setInterval(() => {
            void this._refreshRows();
        }, ROW_REFRESH_INTERVAL_MS);
    }
    _stopAutoRefresh() {
        if (this._refreshIntervalId === null) {
            return;
        }
        window.clearInterval(this._refreshIntervalId);
        this._refreshIntervalId = null;
    }
    async _refreshRows(showLoading = false) {
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
        }
        catch (error) {
            const nextError = error instanceof Error ? error.message : "Unknown websocket error";
            const errorChanged = this._errorMessage !== nextError;
            this._errorMessage = nextError;
            if (!showLoading && errorChanged) {
                this._syncTableViewState();
            }
        }
        finally {
            this._isRefreshing = false;
            if (showLoading) {
                this._isLoading = false;
                this._render();
            }
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
    _syncSearchInputState() {
        const input = this.querySelector(".search-input");
        if (!input) {
            return;
        }
        input.placeholder = `Search ${this._rows.length} devices`;
        input.value = this._searchText;
        input.addEventListener("input", this._handleSearchInput);
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
        tableView.rows = this._filterRows(this._rows);
        tableView.isLoading = this._isLoading;
        tableView.errorMessage = this._errorMessage;
    }
    _handleSearchInput = (event) => {
        const input = event.currentTarget;
        this._searchText = input.value;
        this._syncTableViewState();
    };
    _handleVisibilityChange = () => {
        if (document.visibilityState !== "visible") {
            return;
        }
        void this._refreshRows();
    };
    _filterRows(rows) {
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
            return (deviceName.includes(search) ||
                batteryType.includes(search) ||
                area.includes(search) ||
                floor.includes(search) ||
                lastReplaced.includes(search));
        });
    }
    _buildRowsSignature(rows) {
        return rows
            .map((row) => [
            row.subentry_id,
            row.device_name,
            row.area ?? "",
            row.floor ?? "",
            row.last_replaced ?? "",
            row.battery_type,
            row.battery_quantity ?? "",
            row.battery_percentage ?? "",
            row.battery_low ? "1" : "0",
        ].join("|"))
            .join("\n");
    }
}
if (!customElements.get("battery-notes-panel")) {
    customElements.define("battery-notes-panel", BatteryNotesPanel);
}

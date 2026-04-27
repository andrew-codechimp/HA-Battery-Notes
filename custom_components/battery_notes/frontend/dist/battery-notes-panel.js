// Material Design Icons v7.4.47
var mdiChevronDown = "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z";
var mdiClose = "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z";
var mdiFormatListChecks = "M3,5H9V11H3V5M5,7V9H7V7H5M11,7H21V9H11V7M11,15H21V17H11V15M5,20L1.5,16.5L2.91,15.09L5,17.17L9.59,12.59L11,14L5,20Z";

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
            battery_low: parseBatteryLow(record.battery_low),
        };
    });
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
    _selectionMode = false;
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
    set selectionMode(selectionMode) {
        this._selectionMode = selectionMode;
        this._queueRender();
    }
    connectedCallback() {
        this._queueRender();
    }
    selectAllRows() {
        const table = this.querySelector("#battery-notes-table");
        table?.selectAll?.();
    }
    clearSelectedRows() {
        const table = this.querySelector("#battery-notes-table");
        table?.clearSelection?.();
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
            const table = this.querySelector("#battery-notes-table");
            table?.addEventListener("selection-changed", this._handleSelectionChanged);
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
    _handleSelectionChanged = (event) => {
        const detail = event.detail;
        const selectedIds = Array.isArray(detail?.value) ? detail.value : [];
        this.dispatchEvent(new CustomEvent("battery-notes-selection-changed", {
            detail: selectedIds,
            bubbles: true,
            composed: true,
        }));
    };
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
    _selectionMode = false;
    _selectedIds = [];
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
        this.addEventListener("battery-notes-selection-changed", this._handleSelectionChanged);
        document.addEventListener("visibilitychange", this._handleVisibilityChange);
        this._startAutoRefresh();
        if (!this.querySelector(".panel")) {
            this._render();
        }
    }
    disconnectedCallback() {
        this.removeEventListener("battery-notes-selection-changed", this._handleSelectionChanged);
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
          cursor: pointer;
        }

        .select-mode-chip {
          --md-assist-chip-icon-label-space: 0;
          --md-assist-chip-trailing-space: 8px;
        }

        ha-assist-chip {
          --ha-assist-chip-container-shape: 10px;
          --ha-assist-chip-container-color: var(--card-background-color);
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

        .selection-menu-chip {
          --ha-assist-chip-container-color: color-mix(in srgb, var(--app-header-text-color, white) 12%, transparent);
          --ha-assist-chip-label-text-color: var(--app-header-text-color, white);
          --ha-assist-chip-icon-color: var(--app-header-text-color, white);
        }

        .selection-menu-icon {
          width: 18px;
          height: 18px;
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
          <ha-icon-button
            class="selection-close"
            title="Exit selection mode"
            label="Exit selection mode"
            path="${mdiClose}"
          ></ha-icon-button>
          <ha-button-menu class="selection-menu" corner="BOTTOM_START" fixed>
            <ha-assist-chip slot="trigger" class="selection-menu-chip" title="Selection actions">
              <ha-svg-icon slot="icon" class="selection-menu-icon" path="${mdiChevronDown}"></ha-svg-icon>
              Selection
            </ha-assist-chip>
            <ha-list-item class="selection-menu-item" data-action="all">Select all</ha-list-item>
            <ha-list-item class="selection-menu-item" data-action="none">Select none</ha-list-item>
            <ha-list-item class="selection-menu-item" data-action="exit">Exit selection mode</ha-list-item>
          </ha-button-menu>
          <p class="selection-header-title">0 selected</p>
        </div>
        <div class="content">
          <div class="table-header">
            <div class="header-actions">
              <ha-assist-chip class="selection-mode-button select-mode-chip" title="Enter selection mode">
                <ha-svg-icon slot="icon" path="${mdiFormatListChecks}"></ha-svg-icon>
              </ha-assist-chip>
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
    _syncSearchInputState() {
        const input = this.querySelector(".search-input");
        if (!input) {
            return;
        }
        input.placeholder = `Search ${this._rows.length} devices`;
        input.value = this._searchText;
        input.addEventListener("input", this._handleSearchInput);
    }
    _syncSelectionActionState() {
        const selectButton = this.querySelector(".selection-mode-button");
        if (!selectButton) {
            return;
        }
        selectButton.addEventListener("click", this._handleSelectionModeStart);
    }
    _syncSelectionHeaderState() {
        const header = this.querySelector(".selection-header");
        const title = this.querySelector(".selection-header-title");
        const close = this.querySelector(".selection-close");
        const mainHeader = this.querySelector(".main-header");
        if (!header || !title || !close || !mainHeader) {
            return;
        }
        const selectButton = this.querySelector(".selection-mode-button");
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
        close.onclick = this._handleSelectionModeExit;
        const menuItems = this.querySelectorAll(".selection-menu-item");
        menuItems.forEach((item) => {
            item.onclick = this._handleSelectionMenuAction;
        });
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
        tableView.selectionMode = this._selectionMode;
    }
    _handleSearchInput = (event) => {
        const input = event.currentTarget;
        this._searchText = input.value;
        this._syncTableViewState();
    };
    _handleSelectionModeStart = () => {
        this._selectionMode = true;
        this._syncSelectionHeaderState();
        this._syncTableViewState();
    };
    _handleSelectionModeExit = () => {
        this._selectionMode = false;
        this._selectedIds = [];
        this._syncTableViewState();
        this._syncSelectionHeaderState();
    };
    _handleSelectionMenuAction = (event) => {
        const action = event.currentTarget.dataset.action;
        const tableView = this.querySelector("battery-notes-table-view");
        if (action === "all") {
            tableView?.selectAllRows?.();
            return;
        }
        if (action === "none") {
            tableView?.clearSelectedRows?.();
            this._selectedIds = [];
            this._syncSelectionHeaderState();
            return;
        }
        if (action === "exit") {
            this._handleSelectionModeExit();
        }
    };
    _handleSelectionChanged = (event) => {
        const selectedIds = event.detail;
        this._selectedIds = Array.isArray(selectedIds) ? selectedIds : [];
        this._syncSelectionHeaderState();
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
            return deviceName.includes(search) || batteryType.includes(search);
        });
    }
    _buildRowsSignature(rows) {
        return rows
            .map((row) => [
            row.subentry_id,
            row.device_name,
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

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
    _selectionMode = false;
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
    set selectionMode(selectionMode) {
        this._selectionMode = selectionMode;
        this._render();
    }
    connectedCallback() {
        this._render();
    }
    selectAllRows() {
        const table = this.querySelector("#battery-notes-table");
        table?.selectAll?.();
    }
    clearSelectedRows() {
        const table = this.querySelector("#battery-notes-table");
        table?.clearSelection?.();
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
        table.selectable = this._selectionMode;
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
        table.addEventListener("selection-changed", (event) => {
            const detail = event.detail;
            const selectedIds = Array.isArray(detail?.value) ? detail.value : [];
            this.dispatchEvent(new CustomEvent("battery-notes-selection-changed", {
                detail: selectedIds,
                bubbles: true,
                composed: true,
            }));
        });
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
    _searchText = "";
    _selectionMode = false;
    _selectedIds = [];
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
        this.addEventListener("battery-notes-selection-changed", this._handleSelectionChanged);
        this._render();
    }
    disconnectedCallback() {
        this.removeEventListener("battery-notes-selection-changed", this._handleSelectionChanged);
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
    _handleSelectionChanged = (event) => {
        const selectedIds = event.detail;
        this._selectedIds = Array.isArray(selectedIds) ? selectedIds : [];
        this._syncSelectionHeaderState();
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
}
if (!customElements.get("battery-notes-panel")) {
    customElements.define("battery-notes-panel", BatteryNotesPanel);
}

type HassLike = {
  callWS: (msg: { type: string }) => Promise<unknown>;
};

class BatteryNotesHeaderView extends HTMLElement {
  private _hass: HassLike | null = null;

  private _narrow = false;

  set hass(hass: HassLike | null) {
    this._hass = hass;
    this._syncMenuButton();
  }

  set narrow(narrow: boolean) {
    this._narrow = narrow;
    this._syncMenuButton();
  }

  connectedCallback(): void {
    this._render();
  }

  private _render(): void {
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

  private _syncMenuButton(): void {
    const menuButton = this.querySelector("ha-menu-button") as
      | { hass?: HassLike; narrow?: boolean }
      | null;

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

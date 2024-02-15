import { LitElement, html, CSSResultGroup, css, TemplateResult } from "lit";
import { property, customElement } from "lit/decorators.js";
import { loadHaForm } from "./load-ha-elements";

import { commonStyle } from "./styles";
import { Dictionary, HomeAssistant } from "./types";
import { localize } from "../localize/localize";

import { documentationUrl } from "./const";

import { mdiFileDocument } from "@mdi/js";

// import { IconOverflowMenuItem } from "../../homeassistant-frontend/src/components/ha-icon-overflow-menu";
// import { mainWindow } from "../../homeassistant-frontend/src/common/dom/get_main_window";

@customElement("battery-panel")
export class BatteryPanel extends LitElement {
  @property({ attribute: false }) public hass!: HomeAssistant;
  @property({ type: Boolean, reflect: true }) public narrow!: boolean;

  async firstUpdated() {
    window.addEventListener("location-changed", () => {
      if (!window.location.pathname.includes("battery-notes")) return;
      this.requestUpdate();
    });

    await loadHaForm();
    this.requestUpdate();
  }

  protected render(): TemplateResult | void {
    return html`
      <div class="header">
        <div class="toolbar">
          <ha-menu-button
            .hass=${this.hass}
            .narrow=${this.narrow}
          ></ha-menu-button>
          <div class="main-title">${localize("title", this.hass.language)}</div>
        </div>
      </div>
    `;
  }

  static get styles(): CSSResultGroup {
    return css`
      ${commonStyle} :host {
        color: var(--primary-text-color);
        --paper-card-header-color: var(--primary-text-color);
      }
      .header {
        background-color: var(--app-header-background-color);
        color: var(--app-header-text-color, white);
        border-bottom: var(--app-header-border-bottom, none);
      }
      .toolbar {
        height: var(--header-height);
        display: flex;
        align-items: center;
        font-size: 20px;
        padding: 0 16px;
        font-weight: 400;
        box-sizing: border-box;
      }
      .main-title {
        margin: 0 0 0 24px;
        line-height: 20px;
        flex-grow: 1;
      }
      ha-tabs {
        margin-left: max(env(safe-area-inset-left), 24px);
        margin-right: max(env(safe-area-inset-right), 24px);
        --paper-tabs-selection-bar-color: var(
          --app-header-selection-bar-color,
          var(--app-header-text-color, #fff)
        );
        text-transform: uppercase;
      }

      .view {
        height: calc(100vh - 112px);
        display: flex;
        justify-content: center;
      }

      .view > * {
        width: 600px;
        max-width: 600px;
      }

      .view > *:last-child {
        margin-bottom: 20px;
      }

      .version {
        font-size: 14px;
        font-weight: 500;
        color: rgba(var(--rgb-text-primary-color), 0.9);
      }
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    "battery-panel": BatteryPanel;
  }
}

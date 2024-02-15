import { LitElement, html, CSSResultGroup, css, TemplateResult } from "lit";
import { property, customElement } from "lit/decorators.js";
import { loadHaForm } from "./load-ha-elements";

import { commonStyle } from "./styles";
import { Dictionary, HomeAssistant } from "./types";
import { localize } from "../localize/localize";

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
}

declare global {
  interface HTMLElementTagNameMap {
    "battery-panel": BatteryPanel;
  }
}

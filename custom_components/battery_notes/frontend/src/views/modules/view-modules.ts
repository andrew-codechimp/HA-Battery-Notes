import { TemplateResult, LitElement, html, css, CSSResultGroup } from "lit";
import { query } from "lit/decorators.js";
import { property, customElement } from "lit/decorators.js";
import { HomeAssistant } from "custom-card-helpers";
import { loadHaForm } from "../../load-ha-elements";
import { UnsubscribeFunc } from "home-assistant-js-websocket";
import {
  deleteModule,
  fetchConfig,
  fetchAllModules,
  fetchModules,
  saveModule,
  fetchZones,
} from "../../data/websockets";
import { SubscribeMixin } from "../../subscribe-mixin";

import {
  SmartIrrigationConfig,
  SmartIrrigationZone,
  SmartIrrigationModule,
} from "../../types";
import { commonStyle } from "../../styles";
import { localize } from "../../../localize/localize";
import { DOMAIN } from "../../const";
import { prettyPrint, getPart } from "../../helpers";
import { mdiDelete } from "@mdi/js";

@customElement("smart-irrigation-view-modules")
class SmartIrrigationViewModules extends SubscribeMixin(LitElement) {
  hass?: HomeAssistant;
  @property() config?: SmartIrrigationConfig;

  @property({ type: Array })
  private zones: SmartIrrigationZone[] = [];
  @property({ type: Array })
  private modules: SmartIrrigationModule[] = [];
  @property({ type: Array })
  private allmodules: SmartIrrigationModule[] = [];

  @query("#moduleInput")
  private moduleInput!: HTMLSelectElement;

  firstUpdated() {
    (async () => await loadHaForm())();
  }

  public hassSubscribe(): Promise<UnsubscribeFunc>[] {
    this._fetchData();
    return [
      this.hass!.connection.subscribeMessage(() => this._fetchData(), {
        type: DOMAIN + "_config_updated",
      }),
    ];
  }

  private async _fetchData(): Promise<void> {
    if (!this.hass) {
      return;
    }
    this.config = await fetchConfig(this.hass);
    this.zones = await fetchZones(this.hass);
    this.modules = await fetchModules(this.hass);
    this.allmodules = await fetchAllModules(this.hass);
    /*Object.entries(this.modules).forEach(([key, value]) =>
      console.log(key, value)
    );*/
  }

  private handleAddModule(): void {
    const m = this.allmodules.filter(
      (o) => o.name == this.moduleInput.selectedOptions[0].text
    )[0];
    if (!m) {
      return;
    }
    const newModule: SmartIrrigationModule = {
      id: this.modules.length,
      name: this.moduleInput.selectedOptions[0].text,
      description: m.description,
      config: m.config,
      schema: m.schema,
    };
    this.modules = [...this.modules, newModule];

    this.saveToHA(newModule);
  }

  private handleRemoveModule(ev: Event, index: number): void {
    this.modules = this.modules.filter((_, i) => i !== index);
    if (!this.hass) {
      return;
    }
    deleteModule(this.hass, index.toString());
  }

  private saveToHA(module: SmartIrrigationModule): void {
    if (!this.hass) {
      return;
    }
    saveModule(this.hass, module);
    //get latest version from HA
    this._fetchData();
  }
  private renderModule(
    module: SmartIrrigationModule,
    index: number
  ): TemplateResult {
    if (!this.hass) {
      return html``;
    } else {
      const numberofzonesusingthismodule = this.zones.filter(
        (o) => o.module === module.id
      ).length;
      return html`
        <ha-card header="${module.id}: ${module.name}">
          <div class="card-content">
            <div class="moduledescription${index}">${module.description}</div>
            <div class="moduleconfig">
              <label class="subheader"
                >${localize(
                  "panels.modules.cards.module.labels.configuration",
                  this.hass.language
                )}
                (*
                ${localize(
                  "panels.modules.cards.module.labels.required",
                  this.hass.language
                )})</label
              >
              ${module.schema
                ? Object.entries(module.schema).map(([value]) =>
                    this.renderConfig(index, value)
                  )
                : null}
            </div>
            ${numberofzonesusingthismodule
              ? html` ${localize(
                  "panels.modules.cards.module.errors.cannot-delete-module-because-zones-use-it",
                  this.hass.language
                )}`
              : html` <svg
                  style="width:24px;height:24px"
                  viewBox="0 0 24 24"
                  id="deleteZone${index}"
                  @click="${(e: Event) => this.handleRemoveModule(e, index)}"
                >
                  <title>
                    ${localize("common.actions.delete", this.hass.language)}
                  </title>
                  <path fill="#404040" d="${mdiDelete}" />
                </svg>`}
          </div>
        </ha-card>
      `;
    }
  }

  /*
  : html`<div class="schemaline">
                    <input
                      id="moduleconfigInput${index}"
                      type="text"
                      .value=${JSON.stringify(module.config)}
                    />
                  </div>`
                  */
  renderConfig(index: number, value: string): any {
    const mod = Object.values(this.modules).at(index);
    if (!mod || !this.hass) {
      return;
    }
    //loop over items in schema and output the right UI
    const schemaline = mod.schema[value];
    const name = schemaline["name"];
    const prettyName = prettyPrint(name);
    let val = "";
    if (mod.config == null) {
      mod.config = [];
    }
    if (name in mod.config) {
      val = mod.config[name];
    }
    let r = html`<label for="${name + index}"
      >${prettyName} </label
    `;
    if (schemaline["type"] == "boolean") {
      r = html`${r}<input
          type="checkbox"
          id="${name + index}"
          .checked=${val}
          @input="${(e: Event) =>
            this.handleEditConfig(index, {
              ...mod,
              config: {
                ...mod.config,
                [name]: (e.target as HTMLInputElement).checked,
              },
            })}"
        />`;
    } else if (
      schemaline["type"] == "float" ||
      schemaline["type"] == "integer"
    ) {
      r = html`${r}<input
          type="number"
          class="shortinput"
          id="${schemaline["name"] + index}"
          .value="${mod.config[schemaline["name"]]}"
          @input="${(e: Event) =>
            this.handleEditConfig(index, {
              ...mod,
              config: {
                ...mod.config,
                [name]: (e.target as HTMLInputElement).value,
              },
            })}"
        />`;
    } else if (schemaline["type"] == "string") {
      r = html`${r}<input
          type="text"
          id="${name + index}"
          .value="${val}"
          @input="${(e: Event) =>
            this.handleEditConfig(index, {
              ...mod,
              config: {
                ...mod.config,
                [name]: (e.target as HTMLInputElement).value,
              },
            })}"
        />`;
    } else if (schemaline["type"] == "select") {
      const hasslanguage = this.hass.language;
      //@change
      r = html`${r}<select
          id="${name + index}"
          @change="${(e: Event) =>
            this.handleEditConfig(index, {
              ...mod,
              config: {
                ...mod.config,
                [name]: (e.target as HTMLSelectElement).value,
              },
            })}"
        >
          ${Object.entries(schemaline["options"]).map(
            ([key, value]) =>
              html`<option
                value="${getPart(value, 0)}"
                ?selected="${val === getPart(value, 0)}"
              >
                ${localize(
                  "panels.modules.cards.module.translated-options." +
                    getPart(value, 1),
                  hasslanguage
                )}
              </option>`
          )}
        </select>`;
    }

    if (schemaline["required"]) {
      r = html`${r} *`;
    }
    r = html`<div class="schemaline">${r}</div>`;
    return r;
  }

  handleEditConfig(index: number, updatedModule: SmartIrrigationModule) {
    this.modules = Object.values(this.modules).map((module, i) =>
      i === index ? updatedModule : module
    );
    this.saveToHA(updatedModule);
  }

  private renderOption(value: any, description: any): TemplateResult {
    if (!this.hass) {
      return html``;
    } else {
      return html`<option value="${value}>${description}</option>`;
    }
  }
  render(): TemplateResult {
    if (!this.hass) {
      return html``;
    } else {
      return html`
        <ha-card
          header="${localize("panels.modules.title", this.hass.language)}"
        >
          <div class="card-content">
            ${localize("panels.modules.description", this.hass.language)}
          </div>
        </ha-card>
        <ha-card
          header="${localize(
            "panels.modules.cards.add-module.header",
            this.hass.language
          )}"
        >
          <div class="card-content">
            <label for="moduleInput"
              >${localize("common.labels.module", this.hass.language)}:</label
            >
            <select id="moduleInput">
              ${Object.entries(this.allmodules).map(
                ([key, value]) =>
                  html`<option value="${value.id}">${value.name}</option>`
              )}
            </select>
            <button @click="${this.handleAddModule}">
              ${localize(
                "panels.modules.cards.add-module.actions.add",
                this.hass.language
              )}
            </button>
          </div>
        </ha-card>

        ${Object.entries(this.modules).map(([key, value]) =>
          this.renderModule(value, parseInt(key))
        )}
      `;
    }
  }

  /*
   ${Object.entries(this.modules).map(([key, value]) =>
          this.renderModule(value, value["id"])
        )}
        */

  static get styles(): CSSResultGroup {
    return css`
      ${commonStyle}
      .zone {
        margin-top: 25px;
        margin-bottom: 25px;
      }
      .hidden {
        display: none;
      }
      .shortinput {
        width: 50px;
      }
      .subheader {
        font-weight: bold;
      }
    `;
  }
}

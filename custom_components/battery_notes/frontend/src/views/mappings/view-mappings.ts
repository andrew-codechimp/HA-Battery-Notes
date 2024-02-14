import { TemplateResult, LitElement, html, css, CSSResultGroup } from "lit";
import { query } from "lit/decorators.js";
import { property, customElement } from "lit/decorators.js";
import { HomeAssistant } from "custom-card-helpers";
import { loadHaForm } from "../../load-ha-elements";
import { UnsubscribeFunc } from "home-assistant-js-websocket";
import {
  deleteMapping,
  fetchConfig,
  fetchMappings,
  saveMapping,
  fetchZones,
} from "../../data/websockets";
import { SubscribeMixin } from "../../subscribe-mixin";

import {
  SmartIrrigationConfig,
  SmartIrrigationZone,
  SmartIrrigationMapping,
} from "../../types";
import { commonStyle } from "../../styles";
import { localize } from "../../../localize/localize";
import {
  DOMAIN,
  MAPPING_CONF_AGGREGATE,
  MAPPING_CONF_AGGREGATE_OPTIONS,
  MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT,
  //removing this as part of beta12. Temperature is the only thing we want to take and we will apply min and max aggregation on our own.
  //MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_MAX_TEMP,
  //MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_MIN_TEMP,
  MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_PRECIPITATION,
  MAPPING_CONF_SENSOR,
  MAPPING_CONF_SOURCE,
  MAPPING_CONF_SOURCE_NONE,
  MAPPING_CONF_SOURCE_OWM,
  MAPPING_CONF_SOURCE_SENSOR,
  MAPPING_CONF_SOURCE_STATIC_VALUE,
  MAPPING_CONF_STATIC_VALUE,
  MAPPING_CONF_UNIT,
  MAPPING_DEWPOINT,
  MAPPING_EVAPOTRANSPIRATION,
  MAPPING_HUMIDITY,
  //removing this as part of beta12. Temperature is the only thing we want to take and we will apply min and max aggregation on our own.
  //MAPPING_MAX_TEMP,
  //MAPPING_MIN_TEMP,
  MAPPING_PRECIPITATION,
  MAPPING_PRESSURE,
  MAPPING_SOLRAD,
  MAPPING_TEMPERATURE,
  MAPPING_WINDSPEED,
  MAPPING_CONF_PRESSURE_TYPE,
  MAPPING_CONF_PRESSURE_ABSOLUTE,
  MAPPING_CONF_PRESSURE_RELATIVE,
} from "../../const";
import { prettyPrint, getOptionsForMappingType } from "../../helpers";
import { mdiDelete } from "@mdi/js";
import moment from "moment";

@customElement("smart-irrigation-view-mappings")
class SmartIrrigationViewMappings extends SubscribeMixin(LitElement) {
  hass?: HomeAssistant;
  @property() config?: SmartIrrigationConfig;

  @property({ type: Array })
  private zones: SmartIrrigationZone[] = [];
  @property({ type: Array })
  private mappings: SmartIrrigationMapping[] = [];
  //@property({ type: Array })
  //private allmodules: SmartIrrigationModule[] = [];

  @query("#mappingNameInput")
  private mappingNameInput!: HTMLInputElement;

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
    this.mappings = await fetchMappings(this.hass);
    //this.allmodules = await fetchAllModules(this.hass);
    /*Object.entries(this.mappings).forEach(([key, value]) =>
      console.log(key, value)
    );*/
  }

  private handleAddMapping(): void {
    const the_mappings = {
      [MAPPING_DEWPOINT]: "",
      [MAPPING_EVAPOTRANSPIRATION]: "",
      [MAPPING_HUMIDITY]: "",
      //removing this as part of beta12. Temperature is the only thing we want to take and we will apply min and max aggregation on our own.
      //[MAPPING_MAX_TEMP]: "",
      //[MAPPING_MIN_TEMP]: "",
      [MAPPING_PRECIPITATION]: "",
      [MAPPING_PRESSURE]: "",
      [MAPPING_SOLRAD]: "",
      [MAPPING_TEMPERATURE]: "",
      [MAPPING_WINDSPEED]: "",
    };
    const newMapping: SmartIrrigationMapping = {
      id: this.mappings.length,
      name: this.mappingNameInput.value,
      mappings: the_mappings,
    };
    this.mappings = [...this.mappings, newMapping];

    this.saveToHA(newMapping);
    //get latest version from HA
    this._fetchData();
  }

  private handleRemoveMapping(ev: Event, index: number): void {
    this.mappings = this.mappings.filter((_, i) => i !== index);
    if (!this.hass) {
      return;
    }
    deleteMapping(this.hass, index.toString());
  }

  private handleEditMapping(
    index: number,
    updatedMapping: SmartIrrigationMapping
  ): void {
    this.mappings = Object.values(this.mappings).map((mapping, i) =>
      i === index ? updatedMapping : mapping
    );
    this.saveToHA(updatedMapping);
  }
  private saveToHA(mapping: SmartIrrigationMapping): void {
    if (!this.hass) {
      return;
    }
    saveMapping(this.hass, mapping);
  }
  private renderMapping(
    mapping: SmartIrrigationMapping,
    index: number
  ): TemplateResult {
    if (!this.hass) {
      return html``;
    } else {
      const numberofzonesusingthismapping = this.zones.filter(
        (o) => o.mapping === mapping.id
      ).length;
      //below here we should go over all the mappings on the mapping object
      return html`
        <ha-card header="${mapping.id}: ${mapping.name}">
        <div class="card-content">
          <div class="card-content">
            <label for="name${mapping.id}"
              >${localize(
                "panels.mappings.labels.mapping-name",
                this.hass.language
              )}:</label
            >
            <input
              id="name${mapping.id}"
              type="text"
              .value="${mapping.name}"
              @input="${(e: Event) =>
                this.handleEditMapping(index, {
                  ...mapping,
                  name: (e.target as HTMLInputElement).value,
                })}"
            />
            ${Object.entries(mapping.mappings).map(([value]) =>
              this.renderMappingSetting(index, value)
            )}
            ${
              numberofzonesusingthismapping
                ? html`${localize(
                    "panels.mappings.cards.mapping.errors.cannot-delete-mapping-because-zones-use-it",
                    this.hass.language
                  )}`
                : html` <svg
                    style="width:24px;height:24px"
                    viewBox="0 0 24 24"
                    id="deleteZone${index}"
                    @click="${(e: Event) => this.handleRemoveMapping(e, index)}"
                  >
                    <title>
                      ${localize("common.actions.delete", this.hass.language)}
                    </title>
                    <path fill="#404040" d="${mdiDelete}" />
                  </svg>`
            }
          </div>
        </ha-card>
      `;
    }
  }
  renderMappingSetting(index: number, value: string): any {
    const mapping = Object.values(this.mappings).at(index);
    if (!mapping || !this.hass) {
      return;
    }
    //loop over the mappings and output the UI
    const mappingline = mapping.mappings[value];
    let r = html`<div class="mappingsettingname">
      <label for="${value + index}"
        >${localize(
          "panels.mappings.cards.mapping.items." + value.toLowerCase(),
          this.hass.language
        )}
      </label>
    </div> `;
    //source radiobutton: (OWM/sensor/static value) or (none/sensor/static value)
    //show sensor entity input box only if sensor source is selected
    //show unit all the time, but set it to the metric value and disable if OWM. Else enable.
    r = html`${r}
      <div class="mappingsettingline">
        <label for="${value + index + MAPPING_CONF_SOURCE}"
          >${localize(
            "panels.mappings.cards.mapping.source",
            this.hass.language
          )}:</label
        >
      </div>`;

    if (value == MAPPING_EVAPOTRANSPIRATION || value == MAPPING_SOLRAD) {
      //this can not come from OWM!
      r = html`${r}
        <input
          type="radio"
          id="${value + index + MAPPING_CONF_SOURCE_NONE}"
          value="${MAPPING_CONF_SOURCE_NONE}"
          name="${value + index + MAPPING_CONF_SOURCE}"
          ?checked="${mappingline[MAPPING_CONF_SOURCE] ===
          MAPPING_CONF_SOURCE_NONE}"
          @change="${(e: Event) =>
            this.handleEditMapping(index, {
              ...mapping,
              mappings: {
                ...mapping.mappings,
                [value]: {
                  ...mapping.mappings[value],
                  source: (e.target as HTMLInputElement).value,
                },
              },
            })}"
        /><label for="${value + index + MAPPING_CONF_SOURCE_NONE}"
          >${localize(
            "panels.mappings.cards.mapping.sources.none",
            this.hass.language
          )}</label
        > `;
    } else {
      let owmclass = "";
      if (!this.config?.use_owm) {
        owmclass = "strikethrough";
      }
      r = html`${r}
        <input
          type="radio"
          id="${value + index + MAPPING_CONF_SOURCE_OWM}"
          value="${MAPPING_CONF_SOURCE_OWM}"
          name="${value + index + MAPPING_CONF_SOURCE}"
          ?enabled="${this.config?.use_owm}"
          ?checked="${this.config?.use_owm &&
          mappingline[MAPPING_CONF_SOURCE] === MAPPING_CONF_SOURCE_OWM}"
          @change="${(e: Event) =>
            this.handleEditMapping(index, {
              ...mapping,
              mappings: {
                ...mapping.mappings,
                [value]: {
                  ...mapping.mappings[value],
                  source: (e.target as HTMLInputElement).value,
                },
              },
            })}"
        /><label
          class="${owmclass}"
          for="${value + index + MAPPING_CONF_SOURCE_OWM}"
          >${localize(
            "panels.mappings.cards.mapping.sources.openweathermap",
            this.hass.language
          )}</label
        >`;
    }
    r = html`${r}
        <input
          type="radio"
          id="${value + index + MAPPING_CONF_SOURCE_SENSOR}"
          value="${MAPPING_CONF_SOURCE_SENSOR}"
          name="${value + index + MAPPING_CONF_SOURCE}"
          ?checked="${
            mappingline[MAPPING_CONF_SOURCE] === MAPPING_CONF_SOURCE_SENSOR
          }"
          @change="${(e: Event) =>
            this.handleEditMapping(index, {
              ...mapping,
              mappings: {
                ...mapping.mappings,
                [value]: {
                  ...mapping.mappings[value],
                  [MAPPING_CONF_SOURCE]: (e.target as HTMLInputElement).value,
                },
              },
            })}"
        /><label for="${value + index + MAPPING_CONF_SOURCE_SENSOR}"
          >${localize(
            "panels.mappings.cards.mapping.sources.sensor",
            this.hass.language
          )}</label
        >
      </div>`;
    r = html`${r}
      <input
        type="radio"
        id="${value + index + MAPPING_CONF_SOURCE_STATIC_VALUE}"
        value="${MAPPING_CONF_SOURCE_STATIC_VALUE}"
        name="${value + index + MAPPING_CONF_SOURCE}"
        ?checked="${
          mappingline[MAPPING_CONF_SOURCE] === MAPPING_CONF_SOURCE_STATIC_VALUE
        }"
        @change="${(e: Event) =>
          this.handleEditMapping(index, {
            ...mapping,
            mappings: {
              ...mapping.mappings,
              [value]: {
                ...mapping.mappings[value],
                [MAPPING_CONF_SOURCE]: (e.target as HTMLInputElement).value,
              },
            },
          })}"
      /><label for="${value + index + MAPPING_CONF_SOURCE_STATIC_VALUE}"
        >${localize(
          "panels.mappings.cards.mapping.sources.static",
          this.hass.language
        )}</label
      >
    </div>`;
    if (mappingline[MAPPING_CONF_SOURCE] == MAPPING_CONF_SOURCE_SENSOR) {
      r = html`${r}
        <div class="mappingsettingline">
          <label for="${value + index + MAPPING_CONF_SENSOR}"
            >${localize(
              "panels.mappings.cards.mapping.sensor-entity",
              this.hass.language
            )}:</label
          >
          <input
            type="text"
            id="${value + index + MAPPING_CONF_SENSOR}"
            value="${mappingline[MAPPING_CONF_SENSOR]}"
            @input="${(e: Event) =>
              this.handleEditMapping(index, {
                ...mapping,
                mappings: {
                  ...mapping.mappings,
                  [value]: {
                    ...mapping.mappings[value],
                    [MAPPING_CONF_SENSOR]: (e.target as HTMLInputElement).value,
                  },
                },
              })}"
          />
        </div>`;
    }
    if (mappingline[MAPPING_CONF_SOURCE] == MAPPING_CONF_SOURCE_STATIC_VALUE) {
      r = html`${r}
        <div class="mappingsettingline">
          <label for="${value + index + MAPPING_CONF_STATIC_VALUE}"
            >${localize(
              "panels.mappings.cards.mapping.static_value",
              this.hass.language
            )}:</label
          >
          <input
            type="text"
            id="${value + index + MAPPING_CONF_STATIC_VALUE}"
            value="${mappingline[MAPPING_CONF_STATIC_VALUE]}"
            @input="${(e: Event) =>
              this.handleEditMapping(index, {
                ...mapping,
                mappings: {
                  ...mapping.mappings,
                  [value]: {
                    ...mapping.mappings[value],
                    [MAPPING_CONF_STATIC_VALUE]: (e.target as HTMLInputElement)
                      .value,
                  },
                },
              })}"
          />
        </div>`;
    }
    if (
      mappingline[MAPPING_CONF_SOURCE] == MAPPING_CONF_SOURCE_SENSOR ||
      mappingline[MAPPING_CONF_SOURCE] == MAPPING_CONF_SOURCE_STATIC_VALUE
    ) {
      r = html`${r}
        <div class="mappingsettingline">
          <label for="${value + index + MAPPING_CONF_UNIT}"
            >${localize(
              "panels.mappings.cards.mapping.input-units",
              this.hass.language
            )}:</label
          >
          <select
            type="text"
            id="${value + index + MAPPING_CONF_UNIT}"
            @change="${(e: Event) =>
              this.handleEditMapping(index, {
                ...mapping,
                mappings: {
                  ...mapping.mappings,
                  [value]: {
                    ...mapping.mappings[value],
                    [MAPPING_CONF_UNIT]: (e.target as HTMLInputElement).value,
                  },
                },
              })}"
          >
            ${this.renderUnitOptionsForMapping(value, mappingline)}
          </select>
        </div>`;

      //specific case for pressure: absolute / relative
      if (value == MAPPING_PRESSURE) {
        r = html`${r}
          <div class="mappingsettingline">
            <label for="${value + index + MAPPING_CONF_PRESSURE_TYPE}"
              >${localize(
                "panels.mappings.cards.mapping.pressure-type",
                this.hass.language
              )}:</label
            >
            <select
              type="text"
              id="${value + index + MAPPING_CONF_PRESSURE_TYPE}"
              @change="${(e: Event) =>
                this.handleEditMapping(index, {
                  ...mapping,
                  mappings: {
                    ...mapping.mappings,
                    [value]: {
                      ...mapping.mappings[value],
                      [MAPPING_CONF_PRESSURE_TYPE]: (
                        e.target as HTMLInputElement
                      ).value,
                    },
                  },
                })}"
            >
              ${this.renderPressureTypes(value, mappingline)}
            </select>
          </div>`;
      }
    }
    if (mappingline[MAPPING_CONF_SOURCE] == MAPPING_CONF_SOURCE_SENSOR) {
      r = html`${r}
        <div class="mappingsettingline">
          <label for="${value + index + MAPPING_CONF_AGGREGATE}"
            >${localize(
              "panels.mappings.cards.mapping.sensor-aggregate-use-the",
              this.hass.language
            )}
          </label>
          <select
            type="text"
            id="${value + index + MAPPING_CONF_AGGREGATE}"
            @change="${(e: Event) =>
              this.handleEditMapping(index, {
                ...mapping,
                mappings: {
                  ...mapping.mappings,
                  [value]: {
                    ...mapping.mappings[value],
                    [MAPPING_CONF_AGGREGATE]: (e.target as HTMLInputElement)
                      .value,
                  },
                },
              })}"
          >
            ${this.renderAggregateOptionsForMapping(value, mappingline)}
          </select>
          <label for="${value + index + MAPPING_CONF_AGGREGATE}"
            >${localize(
              "panels.mappings.cards.mapping.sensor-aggregate-of-sensor-values-to-calculate",
              this.hass.language
            )}</label
          >
        </div>`;
    }

    r = html`<div class="mappingline">${r}</div>`;
    return r;
  }

  private renderAggregateOptionsForMapping(
    value: any,
    mappingline: any
  ): TemplateResult {
    if (!this.hass || !this.config) {
      return html``;
    } else {
      let r = html``;
      let selected = MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT;
      if (value === MAPPING_PRECIPITATION) {
        selected = MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_PRECIPITATION;
      }
      //removing this as part of beta12. Temperature is the only thing we want to take and we will apply min and max aggregation on our own.
      //else if (value === MAPPING_MAX_TEMP) {
      //  selected = MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_MAX_TEMP;
      //}
      //else if (value === MAPPING_MIN_TEMP) {
      //  selected = MAPPING_CONF_AGGREGATE_OPTIONS_DEFAULT_MIN_TEMP;
      //}
      if (mappingline[MAPPING_CONF_AGGREGATE]) {
        selected = mappingline[MAPPING_CONF_AGGREGATE];
      }
      for (const a of MAPPING_CONF_AGGREGATE_OPTIONS) {
        const res = this.renderAggregateOption(a, selected);
        r = html`${r}${res}`;
      }

      return r;
    }
  }

  private renderAggregateOption(agg: any, selected: any): TemplateResult {
    if (!this.hass || !this.config) {
      return html``;
    } else {
      const label_to_use = "panels.mappings.cards.mapping.aggregates." + agg;
      return html`<option value="${agg}" ?selected="${agg === selected}">
        ${localize(label_to_use, this.hass.language)}
      </option>`;
    }
  }

  private renderPressureTypes(value: any, mappingline: any): TemplateResult {
    if (!this.hass || !this.config) {
      return html``;
    } else {
      let r = html``;
      const selected = mappingline[MAPPING_CONF_PRESSURE_TYPE];
      r = html`${r}
        <option
          value="${MAPPING_CONF_PRESSURE_ABSOLUTE}"
          ?selected="${selected === MAPPING_CONF_PRESSURE_ABSOLUTE}"
        >
          ${localize(
            "panels.mappings.cards.mapping.pressure_types." +
              MAPPING_CONF_PRESSURE_ABSOLUTE,
            this.hass.language
          )}
        </option>
        <option
          value="${MAPPING_CONF_PRESSURE_RELATIVE}"
          ?selected="${selected === MAPPING_CONF_PRESSURE_RELATIVE}"
        >
          ${localize(
            "panels.mappings.cards.mapping.pressure_types." +
              MAPPING_CONF_PRESSURE_RELATIVE,
            this.hass.language
          )}
        </option>`;
      return r;
    }
  }
  private renderUnitOptionsForMapping(
    value: any,
    mappingline: any
  ): TemplateResult {
    if (!this.hass || !this.config) {
      return html``;
    } else {
      const theOptions = getOptionsForMappingType(value);
      let r = html``;
      let selected = mappingline[MAPPING_CONF_UNIT];
      const units = this.config.units;
      if (!mappingline[MAPPING_CONF_UNIT]) {
        theOptions.forEach(function (o) {
          if (typeof o.system === "string") {
            if (units == o.system) {
              selected = o.unit;
            }
          } else {
            o.system.forEach(function (element) {
              if (units == element.system) {
                selected = o.unit;
              }
            });
          }
        });
      }
      theOptions.forEach(function (o) {
        r = html`${r}
          <option value="${o.unit}" ?selected="${selected === o.unit}">
            ${o.unit}
          </option>`;
      });
      return r;
    }
  }
  render(): TemplateResult {
    if (!this.hass) {
      return html``;
    } else {
      return html`
        <ha-card
          header="${localize("panels.mappings.title", this.hass.language)}"
        >
          <div class="card-content">
            ${localize("panels.mappings.description", this.hass.language)}.
          </div>
        </ha-card>
        <ha-card
          header="${localize(
            "panels.mappings.cards.add-mapping.header",
            this.hass.language
          )}"
        >
          <div class="card-content">
            <label for="mappingNameInput"
              >${localize(
                "panels.mappings.labels.mapping-name",
                this.hass.language
              )}:</label
            >
            <input id="mappingNameInput" type="text" />
            <button @click="${this.handleAddMapping}">
              ${localize(
                "panels.mappings.cards.add-mapping.actions.add",
                this.hass.language
              )}
            </button>
          </div>
        </ha-card>

        ${Object.entries(this.mappings).map(([key, value]) =>
          this.renderMapping(value, parseInt(key))
        )}
      `;
    }
  }

  /*
  ${Object.entries(this.mappings).map(([key, value]) =>
          this.renderMapping(value, value["id"])
        )}
        */

  static get styles(): CSSResultGroup {
    return css`
      ${commonStyle}
      .mapping {
        margin-top: 25px;
        margin-bottom: 25px;
      }
      .hidden {
        display: none;
      }
      .shortinput {
        width: 50px;
      }
      .mappingsettingname {
        font-weight: bold;
      }
      .mappingline {
        margin-top: 25px;
      }
      .strikethrough {
        text-decoration: line-through;
      }
    `;
  }
}

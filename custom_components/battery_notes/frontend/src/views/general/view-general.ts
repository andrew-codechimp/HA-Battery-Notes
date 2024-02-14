import { CSSResultGroup, LitElement, css, html } from "lit";
import { property, customElement } from "lit/decorators.js";
import { HomeAssistant } from "custom-card-helpers";
import { UnsubscribeFunc } from "home-assistant-js-websocket";

import { fetchConfig, saveConfig } from "../../data/websockets";
import { SubscribeMixin } from "../../subscribe-mixin";
import { localize } from "../../../localize/localize";
import { pick, handleError, parseBoolean } from "../../helpers";
import { loadHaForm } from "../../load-ha-elements";
import { SmartIrrigationConfig } from "../../types";
import { commonStyle } from "../../styles";
import { Path } from "../../common/navigation";
import {
  AUTO_UPDATE_SCHEDULE_DAILY,
  AUTO_UPDATE_SCHEDULE_HOURLY,
  AUTO_UPDATE_SCHEDULE_MINUTELY,
  CONF_AUTO_CALC_ENABLED,
  CONF_AUTO_CLEAR_ENABLED,
  CONF_AUTO_UPDATE_ENABLED,
  CONF_AUTO_UPDATE_INTERVAL,
  CONF_AUTO_UPDATE_SCHEDULE,
  CONF_AUTO_UPDATE_TIME,
  CONF_CALC_TIME,
  CONF_CLEAR_TIME,
  DOMAIN,
} from "../../const";
import { mdiInformationOutline } from "@mdi/js";

@customElement("smart-irrigation-view-general")
export class SmartIrrigationViewGeneral extends SubscribeMixin(LitElement) {
  hass?: HomeAssistant;
  @property() narrow!: boolean;
  @property() path!: Path;

  @property() data?: Partial<SmartIrrigationConfig>;

  @property() config?: SmartIrrigationConfig;

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
    this.data = pick(this.config, [
      CONF_CALC_TIME,
      CONF_AUTO_CALC_ENABLED,
      CONF_AUTO_UPDATE_ENABLED,
      CONF_AUTO_UPDATE_SCHEDULE,
      CONF_AUTO_UPDATE_TIME,
      CONF_AUTO_UPDATE_INTERVAL,
      CONF_AUTO_CLEAR_ENABLED,
      CONF_CLEAR_TIME,
    ]);

    /*Object.entries(this.data).forEach(([key, value]) => console.log(key, value));*/
  }

  firstUpdated() {
    (async () => await loadHaForm())();
  }

  render() {
    if (!this.hass || !this.config || !this.data) return html``;
    else {
      let r1 = html` <div class="card-content">
          <svg
            style="width:24px;height:24px"
            viewBox="0 0 24 24"
            id="showautocalcdescription"
            @click="${() => this.toggleInformation("autocalcdescription")}"
          >
            >
            <title>
              ${localize(
                "panels.zones.actions.information",
                this.hass.language
              )}
            </title>
            <path fill="#404040" d="${mdiInformationOutline}" />
          </svg>
        </div>

        <div class="card-content">
          <label class="hidden" id="autocalcdescription">
            ${localize(
              "panels.general.cards.automatic-duration-calculation.description",
              this.hass.language
            )}
          </label>
        </div>
        <div class="card-content">
          <label for="autocalcenabled"
            >${localize(
              "panels.general.cards.automatic-duration-calculation.labels.auto-calc-enabled",
              this.hass.language
            )}:</label
          >
          <input
            type="radio"
            id="autocalcon"
            name="autocalcenabled"
            value="True"
            ?checked="${this.config.autocalcenabled}"
            @change="${(e: Event) => {
              this.saveData({
                autocalcenabled: parseBoolean(
                  (e.target as HTMLInputElement).value
                ),
              });
            }}"
          /><label for="autocalcon"
            >${localize("common.labels.yes", this.hass.language)}</label
          >
          <input
            type="radio"
            id="autocalcoff"
            name="autocalcenabled"
            value="False"
            ?checked="${!this.config.autocalcenabled}"
            @change="${(e: Event) => {
              this.saveData({
                autocalcenabled: parseBoolean(
                  (e.target as HTMLInputElement).value
                ),
              });
            }}"
          /><label for="autocalcoff"
            >${localize("common.labels.no", this.hass.language)}</label
          >
        </div>`;
      if (this.data.autocalcenabled) {
        r1 = html`${r1}
          <div class="card-content">
            <label for="calctime"
              >${localize(
                "panels.general.cards.automatic-duration-calculation.labels.auto-calc-time",
                this.hass.language
              )}</label
            >:
            <input
              id="calctime"
              type="text"
              class="shortinput"
              .value="${this.config.calctime}"
              @input=${(e: Event) => {
                this.saveData({
                  calctime: (e.target as HTMLInputElement).value,
                });
              }}
            />
          </div>`;
      }
      r1 = html`<ha-card
        header="${localize(
          "panels.general.cards.automatic-duration-calculation.header",
          this.hass.language
        )}"
      >
        ${r1}</ha-card
      >`;
      let r2 = html` <div class="card-content">
          <svg
            style="width:24px;height:24px"
            viewBox="0 0 24 24"
            id="showautoupdatedescription"
            @click="${() => this.toggleInformation("autoupdatedescription")}"
          >
            >
            <title>
              ${localize(
                "panels.zones.actions.information",
                this.hass.language
              )}
            </title>
            <path fill="#404040" d="${mdiInformationOutline}" />
          </svg>
        </div>
        <div class="card-content">
          <label class="hidden" id="autoupdatedescription">
            ${localize(
              "panels.general.cards.automatic-update.description",
              this.hass.language
            )}
          </label>
        </div>
        <div class="card-content">
          <label for="autoupdateenabled"
            >${localize(
              "panels.general.cards.automatic-update.labels.auto-update-enabled",
              this.hass.language
            )}:</label
          >
          <input
            type="radio"
            id="autoupdateon"
            name="autoupdateenabled"
            value="True"
            ?checked="${this.config.autoupdateenabled}"
            @change="${(e: Event) => {
              this.saveData({
                autoupdateenabled: parseBoolean(
                  (e.target as HTMLInputElement).value
                ),
              });
            }}"
          /><label for="autoupdateon"
            >${localize("common.labels.yes", this.hass.language)}</label
          >
          <input
            type="radio"
            id="autoupdateoff"
            name="autoupdateenabled"
            value="False"
            ?checked="${!this.config.autoupdateenabled}"
            @change="${(e: Event) => {
              this.saveData({
                autoupdateenabled: parseBoolean(
                  (e.target as HTMLInputElement).value
                ),
              });
            }}"
          /><label for="autoupdateoff"
            >${localize("common.labels.no", this.hass.language)}</label
          >
        </div>`;
      if (this.data.autoupdateenabled) {
        r2 = html`${r2}
          <div class="card-content">
            <label for="autoupdateinterval"
              >${localize(
                "panels.general.cards.automatic-update.labels.auto-update-interval",
                this.hass.language
              )}:</label
            >
            <input
              name="autoupdateinterval"
              class="shortinput"
              type="number"
              value="${this.data.autoupdateinterval}"
              @input="${(e: Event) => {
                this.saveData({
                  autoupdateinterval: parseInt(
                    (e.target as HTMLInputElement).value
                  ),
                });
              }}"
            />
            <select
              type="text"
              id="autoupdateschedule"
              @change="${(e: Event) => {
                this.saveData({
                  autoupdateschedule: (e.target as HTMLInputElement).value,
                });
              }}"
            >
              <option
                value="${AUTO_UPDATE_SCHEDULE_MINUTELY}"
                ?selected="${this.data.autoupdateschedule ===
                AUTO_UPDATE_SCHEDULE_MINUTELY}"
              >
                ${localize(
                  "panels.general.cards.automatic-update.options.minutes",
                  this.hass.language
                )}
              </option>
              <option
                value="${AUTO_UPDATE_SCHEDULE_HOURLY}"
                ?selected="${this.data.autoupdateschedule ===
                AUTO_UPDATE_SCHEDULE_HOURLY}"
              >
                ${localize(
                  "panels.general.cards.automatic-update.options.hours",
                  this.hass.language
                )}
              </option>
              <option
                value="${AUTO_UPDATE_SCHEDULE_DAILY}"
                ?selected="${this.data.autoupdateschedule ===
                AUTO_UPDATE_SCHEDULE_DAILY}"
              >
                ${localize(
                  "panels.general.cards.automatic-update.options.days",
                  this.hass.language
                )}
              </option>
            </select>
          </div>
          <div class="card-content">
            <label for="updatedelay"
              >${localize(
                "panels.general.cards.automatic-update.labels.auto-update-delay",
                this.hass.language
              )}
              (s):</label
            >
            <input
              id="updatedelay"
              type="text"
              class="shortinput"
              .value="${this.config.autoupdatedelay}"
              @input=${(e: Event) => {
                this.saveData({
                  autoupdatedelay: parseInt(
                    (e.target as HTMLInputElement).value
                  ),
                });
              }}
            />
          </div>`;
      }

      r2 = html`<ha-card header="${localize(
        "panels.general.cards.automatic-update.header",
        this.hass.language
      )}",
      this.hass.language)}">${r2}</ha-card>`;

      let r3 = html` <div class="card-content">
          <svg
            style="width:24px;height:24px"
            viewBox="0 0 24 24"
            id="showautocleardescription"
            @click="${() => this.toggleInformation("autocleardescription")}"
          >
            <title>
              ${localize(
                "panels.zones.actions.information",
                this.hass.language
              )}
            </title>

            <path fill="#404040" d="${mdiInformationOutline}" />
          </svg>
        </div>
        <div class="card-content">
          <label class="hidden" id="autocleardescription">
            ${localize(
              "panels.general.cards.automatic-clear.description",
              this.hass.language
            )}
          </label>
        </div>
        <div class="card-content">
          <label for="autoclearenabled"
            >${localize(
              "panels.general.cards.automatic-clear.labels.automatic-clear-enabled",
              this.hass.language
            )}:</label
          >
          <input
            type="radio"
            id="autoclearon"
            name="autoclearenabled"
            value="True"
            ?checked="${this.config.autoclearenabled}"
            @change="${(e: Event) => {
              this.saveData({
                autoclearenabled: parseBoolean(
                  (e.target as HTMLInputElement).value
                ),
              });
            }}"
          /><label for="autoclearon"
            >${localize("common.labels.yes", this.hass.language)}</label
          >
          <input
            type="radio"
            id="autoclearoff"
            name="autoclearenabled"
            value="False"
            ?checked="${!this.config.autoclearenabled}"
            @change="${(e: Event) => {
              this.saveData({
                autoclearenabled: parseBoolean(
                  (e.target as HTMLInputElement).value
                ),
              });
            }}"
          /><label for="autoclearoff"
            >${localize("common.labels.no", this.hass.language)}</label
          >
        </div>`;
      if (this.data.autoclearenabled) {
        r3 = html`${r3}
          <div class="card-content">
            <label for="calctime"
              >${localize(
                "panels.general.cards.automatic-clear.labels.automatic-clear-time",
                this.hass.language
              )}</label
            >:
            <input
              id="cleardatatime"
              type="text"
              class="shortinput"
              .value="${this.config.cleardatatime}"
              @input=${(e: Event) => {
                this.saveData({
                  cleardatatime: (e.target as HTMLInputElement).value,
                });
              }}
            />
          </div>`;
      }
      r3 = html`<ha-card header="${localize(
        "panels.general.cards.automatic-clear.header",
        this.hass.language
      )}" >${r3}</div></ha-card>`;

      const r = html`<ha-card
          header="${localize("panels.general.title", this.hass.language)}"
        >
          <div class="card-content">
            ${localize("panels.general.description", this.hass.language)}
          </div> </ha-card
        >${r2}${r1}${r3}`;

      return r;
    }
  }

  private saveData(changes: Partial<SmartIrrigationConfig>) {
    if (!this.hass || !this.data) return;

    this.data = {
      ...this.data,
      ...changes,
    };
    saveConfig(this.hass, this.data)
      .catch((e) =>
        handleError(e, this.shadowRoot!.querySelector("ha-card") as HTMLElement)
      )
      .then();
  }

  toggleInformation(item: string) {
    const el = this.shadowRoot?.querySelector("#" + item);

    //const bt = this.shadowRoot?.querySelector("#showcalcresults" + index);
    //if (!el || !bt) {
    if (!el) {
      return;
    } else {
      if (el.className != "hidden") {
        el.className = "hidden";
        //bt.textContent = "Show calculation explanation";
      } else {
        el.className = "information";
        //bt.textContent = "Hide explanation";
      }
    }
  }
  static get styles(): CSSResultGroup {
    return css`
      ${commonStyle}
      .hidden {
        display: none;
      }
      .shortinput {
        width: 50px;
      }
      .information {
        margin-left: 20px;
        margin-top: 5px;
      }
    `;
  }
}

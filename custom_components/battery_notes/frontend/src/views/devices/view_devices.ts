/* eslint-disable prettier/prettier */
import { LitElement, html } from 'lit';
import { property, customElement } from 'lit/decorators.js';
import { loadHaForm } from '../../load-ha-elements';
import { HomeAssistant } from '../../types';
import { Path } from '../../common/navigation';

@customElement('batterynotes-view-devices')
export class BatteryNotesViewDevices extends LitElement {
  @property()
  hass?: HomeAssistant;

  @property()
  narrow!: boolean;

  @property()
  path!: Path;

  firstUpdated() {
    (async () => await loadHaForm())();

    // if (this.path && this.path.length == 3 && this.path[0] == 'filter') {
    //   const filterOption = this.path[1];
    //   const filterValue = this.path[2];

    //   if (filterOption == 'area') this.selectedArea = this.path[2];
    //   else if (filterOption == 'mode') {
    //     const res = Object.keys(EArmModes).find(e => EArmModes[e] == filterValue);
    //     if (res) this.selectedMode = res as EArmModes;
    //   }
    // }
  }

  render() {
    if (!this.hass) return html``;

    return html`
        <devices-overview-card
          .hass=${this.hass}
          .narrow=${this.narrow}
        ></devices-overview-card>
        <add-devices-card .hass=${this.hass} .narrow=${this.narrow}></add-devices-card>
      `;
  }
}

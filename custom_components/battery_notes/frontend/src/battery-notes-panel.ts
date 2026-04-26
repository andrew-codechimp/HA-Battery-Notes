class BatteryNotesPanel extends HTMLElement {
  connectedCallback(): void {
    this.innerHTML = `
      <div style="padding: 24px; max-width: 800px; margin: 0 auto;">
        <h1 style="margin: 0 0 8px 0;">Battery Notes</h1>
        <p style="margin: 0; opacity: 0.8;">
          Minimal TS panel registration is working.
        </p>
      </div>
    `;
  }
}

if (!customElements.get("battery-notes-panel")) {
  customElements.define("battery-notes-panel", BatteryNotesPanel);
}

# Battery state and events

[Back to the instruction index](../AGENTS.md)

Read when changing thresholds, event generation, templates, unavailable-state handling, outlier filtering, or update throttling.

## Battery state and event contracts

The coordinator owns battery-state interpretation and shared event payloads;
platform entities observe sources and present the result.

- A per-note threshold of `0` inherits the integration default. Numeric low
  detection uses **level < threshold**; increased detection uses
  **new level >= previous level + increase threshold**.
- Low-state precedence is low-battery template, percentage template/wrapped
  percentage, then wrapped binary battery-low state. Preserve this ordering.
- Threshold events describe transitions into and out of low state. Initialization,
  invalid reports, and repeated unchanged states must not create false transitions.
- Binary/template low-state transitions use nominal event levels of 0 and 100.
  Keep payload semantics consistent with percentage-source events.
- Reuse `event_data` and `battery_level_event_data` for identity, metadata, area,
  and threshold fields. Entity areas take precedence over their device's area.
- `battery_notes_battery_increased` does **not** automatically set the replacement
  date. Users can connect it to `set_battery_replaced` through an automation.
- Handle `unknown`, `unavailable`, invalid template output, recovery, and
  `retain_state` consistently. Preserve the previous valid state/history needed
  for later transitions; do not turn an unavailable battery into a 0% report.
- Preserve `LowOutlierFilter` behavior, including real zero readings and consecutive
  outliers. Use the regression cases in `test_battery_events.py`.
- Wrapped percentage reports and Battery+ state writes are throttled using
  `STATE_WRITE_INTERVAL_SECONDS`. Compare raw levels where required: rounded
  display values must not hide a real change. Availability and replacement-date
  changes must still become visible promptly.
- Keep `_unrecorded_attributes` and write throttling in mind when adding attributes;
  frequently changing metadata should not cause needless recorder writes.

Use `TemplateTrackingMixin` for template entities, including startup scheduling,
error handling, listener cleanup, and loop detection. Avoid duplicating that
machinery in each platform.

## Related guidance

For public action payloads, read [Actions and responses](actions.md). For persisted report history, read [Storage, migrations, and repairs](storage-and-migrations.md).

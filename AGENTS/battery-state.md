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

Source selectors use `battery_notes_source_entity('sensor', 'voltage', 'V')` inside Jinja
expressions and resolve to an entity ID, for example
`states(battery_notes_source_entity('sensor', 'voltage', 'V'))`. Calls require two or three
positional literal string arguments: domain (`sensor` or `binary_sensor`), device
class, and optional unit. Variables, expressions, keyword arguments, and unpacked
arguments are rejected. The function name is case-sensitive; selector fields are
normalized using `casefold`, with `percentage` aliasing `%` in any case.
`SourceTemplateResolver` searches the associated device (or the source entity
itself for a standalone note), excludes disabled/Battery Notes entities, and
requires exactly one match. Live units take precedence over registry fallback
units. Keep source calls in saved configuration. `ParsedTemplate` lexes Jinja once
to identify call spans and parses each call into a typed selector; quoted strings,
comments, raw blocks, and ordinary text are preserved. The old `[[source::...]]`
syntax is no longer resolved. Replace source calls with quoted entity IDs before
creating the tracked `Template`; this is preprocessing, not a global Jinja function.
Registry and source-metadata changes retry resolution; source registry IDs preserve
identity across renames. Rebinding is deferred until state-event dispatch finishes,
with old results suppressed while a refresh is pending. Remove the old tracker
before replacing it, and cancel queued refreshes and resolution listeners on
unload. Resolution errors use the existing template error/retain-state path.

## Related guidance

For public action payloads, read [Actions and responses](actions.md). For persisted report history, read [Storage, migrations, and repairs](storage-and-migrations.md).

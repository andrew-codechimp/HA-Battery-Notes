# Actions and responses

[Back to the instruction index](../AGENTS.md)

Read when adding or changing actions, replacement buttons, targeting, event payloads, or service responses.

## Actions and responses

The public actions are `set_battery_replaced`, `check_battery_last_replaced`,
`check_battery_last_reported`, and `check_battery_low` under `battery_notes`.

- Replacement requires `device_id` or `source_entity_id`. Entity targeting takes
  precedence; device targeting prefers a device note over entity notes sharing
  the device. Unconfigured sources raise a translated `HomeAssistantError`.
- The three check actions support optional responses. `raise_events=False`
  suppresses events without suppressing requested response data.
- `_response_item` converts datetimes to ISO strings for responses. Event payloads
  can contain datetime objects; do not change both formats indiscriminately.
- Preserve response keys, including the existing `check_battery_battery_low` key
  returned by `check_battery_low`. A cosmetic rename would break consumers.
- Last-replaced checks honor a disabled last-replaced sensor. Last-reported
  checks currently select notes with wrapped percentage or binary sources.
- When changing an action, review its schema in `const.py`, registration/handler,
  `services.yaml`, English service translations, icons where relevant, tests,
  and `docs/actions.md`. Review `docs/events.md` and blueprints for event changes.

## Related guidance

For shared event semantics, read [Battery state and events](battery-state.md). For action descriptions, read [Translations and documentation](translations-and-docs.md).

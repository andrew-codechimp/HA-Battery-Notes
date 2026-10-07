# Entity identity and lifecycle

[Back to the instruction index](../AGENTS.md)

Read when adding entities or changing source selection, device association, unique IDs, naming, availability, listeners, or cleanup.

## Identity, source linking, and entity lifecycle

- Support all three source arrangements: a device note, an entity note attached
  to a device, and an entity note without a device.
- When `source_entity_id` is present, the entity's current registry device takes
  precedence over a saved `device_id`. Do not treat an entity note as a device
  note just because both IDs exist.
- `calc_config_attributes` creates subentry unique IDs with the `bn_` prefix.
  Platform unique IDs use `subentry.unique_id + description.unique_id_suffix`.
  Suffixes already include their leading underscore. The coordinator's own
  `unique_id` is a different identifier; do not substitute it for entity IDs.
- Preserve existing unique IDs, suffixes, and registry associations unless the
  task includes a migration. Renaming a note should not create replacement
  entities or lose user entity customizations.
- Extend `BatteryNotesEntity` and the appropriate HA platform entity class. Pass
  `config_subentry_id=subentry.subentry_id` when adding entities.
- Reuse the base naming, translation placeholders, and device association logic.
  It attaches entities to existing source devices and supports standalone
  entities. Its `available` property combines coordinator and entity availability.
- Automatic source wrapping selects battery-class percentage sensors with `%`
  units, or battery-class binary sensors. Device notes prefer percentage sources. Battery
  voltage sensors must not be mistaken for percentage sources. Units can fall
  back to live state attributes when the registry does not yet contain them.
  Manual entity notes can use other registered entities with templates; entities
  absent from the entity registry are rejected by the flow.
- A missing source leaves a fully initialized orphaned coordinator. Platforms
  skip its entities and services skip it. A delayed link retry can reload the
  entry on recovery or raise a missing-device repair issue.
- Register entity listeners with `async_on_remove` and entry timers/listeners
  with `async_on_unload`. Check cleanup across reloads, source renames, and removal.
- Respect `RegistryEntryHider.USER`. Cleanup should only undo integration-owned
  hiding. Preserve source-unhiding behavior when notes or the integration are removed.
- `enable_replaced` controls default registry enablement for replacement entities;
  it does not overwrite existing user enable/disable choices.

## Related guidance

For state interpretation, read [Battery state and events](battery-state.md). For source reassociation or removal, also read [Storage, migrations, and repairs](storage-and-migrations.md).

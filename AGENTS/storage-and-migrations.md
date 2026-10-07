# Storage, migrations, and repairs

[Back to the instruction index](../AGENTS.md)

Read when changing persisted history, save scheduling, config versions, repairs, or compatibility with Home Assistant device-registry APIs.

## Persistence, migrations, and HA compatibility

Configuration and battery history are separate. `store.py` uses HA `Store` with
the key `battery_notes.storage`; library files live in the HA configuration
directory under `.storage/battery_notes/`.

- History is keyed by source entity ID for entity notes, and device ID for device
  notes. It holds last-replaced, last-reported, and last-reported-level data.
- Use storage/coordinator methods to change history. Preserve timezone-aware
  datetimes and handling of naive legacy values.
- Normal saves use `SAVE_DELAY`; high-frequency report data uses
  `REPORTED_SAVE_DELAY`. The earliest pending deadline wins so repeated updates
  cannot postpone a write indefinitely.
- Normal subentry removal preserves stored history (`remove_store_entries=False`).
  Do not add automatic history deletion as incidental cleanup. Repair flows have
  their own explicit removal/reassociation behavior.
- Store loading ignores unknown fields for compatibility with newer stored data.
  Its migration also repairs legacy datetime strings. Preserve those behaviors.
- Config version is currently **4**. `async_migrate_integration` consolidates v1/v2
  entries into v3 subentries; `async_migrate_entry` moves v3 advanced settings into
  their nested structure. Storage versioning is separate, currently **1.2**.
- Config migrations must preserve entity ownership, subentry associations, unique
  IDs, and supported user registry settings. Keep ignored entries and unsupported
  future config versions in mind.
- HA 2026.8/2026.9 device-registry compatibility paths are intentional while the
  minimum supported version remains 2026.6. Reuse `common.py` helpers for composite
  devices and related IDs. Do not replace them with newer-only APIs without a
  deliberate compatibility change.
- Composite-device repairs update the source ID and migrate device history while
  retaining note/entity identity. Do not overwrite history already at the target ID.

## Related guidance

For setup and reload behavior, read [Repository and runtime architecture](architecture.md). For registry identity, read [Entity identity and lifecycle](entities.md).

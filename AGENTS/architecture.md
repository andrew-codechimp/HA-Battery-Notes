# Repository and runtime architecture

[Back to the instruction index](../AGENTS.md)

Read when locating an implementation or changing configuration flows, options, runtime data, setup, reload, or subentry removal.

## Repository map

Paths below are relative to `custom_components/battery_notes/` unless specified.

| File | Responsibility |
| --- | --- |
| `__init__.py` | Domain setup, entry setup/unload, migrations, delayed discovery, update listener, subentry removal |
| `config_flow.py` | Initial integration setup, global options, discovery confirmation, manual device/entity subentries, reconfiguration |
| `coordinator.py` | Runtime dataclasses, source linking, per-note state, thresholds/events, access to persisted history |
| `entity.py` | Shared coordinator entity, naming, availability, source-device association, entity descriptions |
| `sensor.py` | Battery type, last-replaced timestamp, wrapped/template Battery+ sensors |
| `binary_sensor.py` | Low-battery entities for percentage, binary, and template sources |
| `button.py` | Battery-replaced button |
| `services.py` / `services.yaml` | Action registration and handlers / UI action definitions |
| `trigger.py` / `triggers.yaml` | Purpose-specific battery event triggers / UI targets and options |
| `const.py` | Domain, platforms, configuration keys, attributes, event names, service schemas, defaults |
| `store.py` | Persistent battery history, migrations, delayed writes, device/entity storage records |
| `library.py` | JSON parsing, indexed library data, model matching, ignored integration domains |
| `library_updater.py` | Downloads, fallback URL, atomic file replacement, update locking, daily scheduling |
| `discovery.py` | Registry scanning, related-device deduplication, discovery flow creation |
| `common.py` | Registry helpers, unhiding sources, composite-device compatibility, repair issue IDs |
| `repairs.py` | Missing-source removal and composite-device reassociation flows |
| `template_helpers.py` | Shared template tracking, startup, cleanup, and self-reference protection |
| `filters.py` | Low-outlier filtering of battery reports |
| `diagnostics.py` | Config entry, per-note runtime, source metadata, and library-match diagnostics |
| `translations/en.json` / `icons.json` | English UI strings / entity and action icons |
| Root `library/` | Community device data and its JSON schema |
| Root `tests/` | Custom-component tests, fixture library, Syrupy snapshots |
| Root `docs/` / `zensical.toml` | Documentation, example blueprints, and site configuration |

## Configuration and runtime architecture

There is one active parent integration entry with multiple `battery_note`
subentries. Do not introduce one parent config entry per device.

| Location | Meaning |
| --- | --- |
| `config_entry.options` | Integration-wide options; several live under `advanced_settings` |
| `config_entry.subentries` | Saved `ConfigSubentry` objects, indexed by `subentry_id` |
| `subentry.data` | Source IDs, battery metadata, per-note thresholds, and advanced settings |
| `subentry.title` | User-visible note name; the name is not persisted as a duplicate data field |
| `config_entry.runtime_data` | `BatteryNotesData` |
| `runtime_data.domain_config` | Shared `BatteryNotesDomainConfig` |
| `runtime_data.store` | Shared `BatteryNotesStorage` |
| `runtime_data.loaded_subentries` | Copies of the subentries loaded at setup, used to detect changes/removals |
| `runtime_data.subentry_coordinators` | One `BatteryNotesSubentryCoordinator` per loaded battery-note subentry |
| `hass.data[MY_KEY]` | Domain config; import the typed key from `coordinator.py` |
| `hass.data[DATA_LIBRARY]` | Library instance; import the typed key from `library.py` |

`BatteryNotesConfigEntry` is `ConfigEntry[BatteryNotesData]`. There is no
`runtime_data.subentries` and no main device coordinator. Operations over loaded
notes use `subentry_coordinators.values()`. Platform setup uses
`get_subentries_of_type(SUBENTRY_BATTERY_NOTE)` to exclude other subentry types.

`async_setup` migrates legacy configuration, loads the store, initializes domain
data and the library, and registers services. `async_setup_entry` reads options,
creates coordinators, forwards platforms, installs the update listener, and
schedules library updates/discovery. Register new actions in
`services.async_setup_services`, not separately for every subentry.

`battery_notes.battery_was_replaced` listens to the existing replacement event from
buttons and actions. Omitting the target includes all battery notes; an explicit
empty target matches none. It resolves standard HA targets for each event, matches
Battery Notes entities through their config subentry, and exposes the unchanged
event fields as top-level members of `trigger`.

`battery_notes.battery_has_increased` shares target matching and listens to the
existing increased event. The coordinator owns numeric increase thresholds and
binary/template recovery detection. The trigger preserves the event payload,
has no options, and does not update the replacement date.

`battery_notes.battery_became_low` shares the same target matching and forwards threshold
events only when `battery_low` is true. Its required `options.event_types` filter accepts
`low_state_transitions`, `reminders`, or `all` (default) to select transitions,
reminders raised by `check_battery_low`, or both. It preserves the existing
threshold event payload.

`battery_notes.battery_no_longer_low` shares the same targets and forwards threshold
events only when `battery_low` is false. It has no reminder option and preserves
the threshold event payload.

`battery_notes.battery_was_not_reported` and `battery_notes.battery_was_not_replaced`
listen to events raised by `check_battery_last_reported` and
`check_battery_last_replaced`, respectively. They share target matching and expose
the unchanged event fields. The check actions own the day limits and scheduling;
these triggers have no options and do not run checks themselves.

Subentry/options changes reload the parent entry. The update listener cleans up
removed notes and sets `skip_library_download` for subentry changes, resetting it
in `finally`. Even when the download is skipped, the delayed setup callback
reloads libraries from disk so changed user-library options take effect.

## Related guidance

For source and registry behavior, read [Entity identity and lifecycle](entities.md). For persisted-data changes, read [Storage, migrations, and repairs](storage-and-migrations.md).

# Battery Notes — coding agent instructions

These instructions apply to this repository. Battery Notes is a Home Assistant
custom integration, distributed through HACS, that associates battery metadata
with existing devices or entities. It provides battery type/quantity, Battery+
percentage sensors, battery-low sensors, replacement timestamps, replacement
buttons, events, and actions. A community JSON library supplies device defaults.

Keep changes focused on the requested behavior. Read the relevant implementation
and tests before editing. Update this guide when architecture or development
commands change; use the code and project configuration to verify details that
may have moved since this guide was written.

This is a separate repository from Home Assistant Core. Use this repository's
`scripts/`, dependencies, tests, and translations workflow. Do not apply Core-only
setup or translation-generation commands here.

## Read the guidance for your task

Before editing, read the documents matching the task below. Read additional
guides when the change crosses functional areas; there is no need to load every
guide for every task. These linked documents contain repository instructions,
not just background reading.

| When to read | Guide |
| --- | --- |
| Setting up the environment, changing Python code or dependencies, running lint/type checks | [Development environment and conventions](AGENTS/development.md) |
| Finding code, changing config/options flows, runtime data, setup, reload, or subentry removal | [Repository and runtime architecture](AGENTS/architecture.md) |
| Adding entities or changing source linking, IDs, naming, availability, listeners, or cleanup | [Entity identity and lifecycle](AGENTS/entities.md) |
| Changing thresholds, events, templates, unavailable-state handling, filtering, or throttling | [Battery state and events](AGENTS/battery-state.md) |
| Changing actions, replacement buttons, targeting, or response payloads | [Actions and responses](AGENTS/actions.md) |
| Changing storage, save scheduling, config migrations, repairs, or HA compatibility | [Storage, migrations, and repairs](AGENTS/storage-and-migrations.md) |
| Changing library data, matching, downloads, user libraries, discovery, or generated library docs | [Library and discovery](AGENTS/library-and-discovery.md) |
| Writing tests, choosing regression coverage, updating snapshots, or validating code changes | [Tests and validation](AGENTS/testing.md) |
| Changing UI strings, translations, user documentation, or example blueprints | [Translations and documentation](AGENTS/translations-and-docs.md) |

## Tasks spanning multiple areas

- For a new entity, read architecture, entities, testing, and translations; also
  read battery state if it interprets battery reports or emits events.
- For a config-flow change, read architecture, testing, and translations; also
  read storage and migrations if saved data changes.
- For an action or replacement-button change, read actions, battery state, and
  testing; read translations and documentation for user-visible changes.
- For source reassociation, removal, or repair, read architecture, entities,
  storage and migrations, and testing.
- For a library-data-only change, start with library and discovery, which includes
  its validation commands. Read testing for matching/discovery implementation changes.

## Maintaining this guidance

Keep this file as the entry point and put detailed rules in the relevant
`AGENTS/` document. Update the index when adding or renaming guides, and preserve
links between related areas. Repository paths in the guides are relative to the
repository root unless stated otherwise.

When architecture changes, update the affected `AGENTS/` guides in the same
change. Keep the repository map, runtime data model, lifecycle rules, and related
contracts aligned with the implementation. Update this index if the change
affects which guides agents should read, and remove or revise obsolete guidance.

Before finishing, inspect the diff and run the checks appropriate to the change.
For documentation-only changes, verify content, links, and formatting; runtime
tests are unnecessary. Report the checks actually run and any blockers.

# Tests and validation

[Back to the instruction index](../AGENTS.md)

Read when writing or changing tests, selecting regression coverage, updating snapshots, or validating implementation changes.

## Tests and validation strategy

Tests use `pytest-homeassistant-custom-component`, real HA registries/state
machinery, and Syrupy snapshots. Asyncio mode is automatic.

- Reuse `tests.setup_integration` and fixtures from `tests/conftest.py`.
  `auto_enable_custom_integrations` is autouse. `mock_config_entry` supplies
  current parent options, including nested advanced settings.
- `battery_note_source` exercises device, entity-with-device, and standalone
  entity notes. Reuse these cases for shared behavior rather than testing only devices.
- `mock_library_updater` prevents real downloads and scheduled update setup;
  `_mock_library_file`, `battery_library`, and `loaded_library` use the small
  `tests/fixtures/library.json`. Use them where relevant; do not depend on the
  changing remote library or a live HA installation.
- Mock external boundaries and use real integration setup for behavior tests.
  Drive state changes, flows, and actions through HA APIs, then await
  `hass.async_block_till_done()` before asserting results.
- Use the `freezer` fixture and `async_fire_time_changed` for timers, retry,
  throttling, and delayed-save tests. Avoid wall-clock sleeps.
- Annotate new test parameters and return types. Prefer concrete HA and fixture
  types, named `pytest.param` cases, and `usefixtures` for unused fixture values.
  Avoid branching test bodies; parameterize shared behavior.
- Use snapshots for substantial entity/flow/diagnostic output, with stable times
  and filtering of incidental identifiers. Update only relevant snapshots with
  `--snapshot-update` and review the resulting `.ambr` diff.

| Change area | Relevant test modules under `tests/` |
| --- | --- |
| Setup, reload, cleanup, source selection | `test_init.py`, `test_init_subentries.py`, `test_common.py` |
| Parent/options flows | `test_config_flow.py` |
| Manual notes and reconfiguration | `test_config_flow_subentries.py` |
| Discovery and confirmation flows | `test_discovery.py`, `test_config_flow_discovery.py` |
| Thresholds, templates, availability, throttling | `test_battery_events.py`, `test_init_subentries.py` |
| Replacement actions/buttons and responses | `test_services.py`, `test_button.py` |
| Battery event trigger targets, reminder filtering, check-action events, payloads, and cleanup | `test_trigger.py` |
| History and config migrations | `test_store.py`, `test_migration.py` |
| Repair issues/reassociation | `test_repairs.py`, `test_init_subentries.py` |
| Library matching/data/downloads | `test_library.py`, `test_library_data.py`, `test_library_updater.py` |
| Diagnostics and UI strings | `test_diagnostics.py`, `test_translations.py` |

Run focused tests while iterating. For integration behavior changes, run the full
suite plus Ruff and mypy before handing off. For documentation-only changes,
check accuracy, paths, formatting, and the diff; a runtime test run is unnecessary.
Report actual checks and any blockers without claiming unrun checks passed.

## Related guidance

For environment setup and lint/type-check commands, read [Development environment and conventions](development.md).

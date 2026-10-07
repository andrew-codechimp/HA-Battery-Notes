# Development environment and conventions

[Back to the instruction index](../AGENTS.md)

Read before setting up the environment, changing Python code or dependencies, or running development tools.

## Environment and commands

Run commands from the repository root. `uv` manages the local `.venv` and
dependencies in `pyproject.toml` and `uv.lock`.

- `.python-version` and `project.requires-python` currently pin Python **3.14.2**.
- The development environment pins Home Assistant **2026.6.0** and
  `pytest-homeassistant-custom-component==0.13.336`.
- `MIN_HA_VERSION` in `const.py` and `hacs.json` currently require HA **2026.6.0**.
- Mypy targets Python 3.14; Ruff currently has `target-version = "py313"`.
  Treat these as separate configuration values; do not change them incidentally.
- Keep the HA/test-plugin pins compatible. The mypy pin has an explanatory
  dependency-compatibility comment in `pyproject.toml`.

| Task | Command |
| --- | --- |
| Set up development environment | `./scripts/setup` |
| Reproduce CI dependency installation | `uv sync --locked` |
| Run all tests | `uv run --no-sync pytest tests -v` |
| Run a focused test module | `uv run --no-sync pytest tests/test_services.py -v` |
| Check Ruff without changing files | `uv run --no-sync ruff check .` |
| Check formatting without changing files | `uv run --no-sync ruff format --check --diff .` |
| Check integration types | `uv run --no-sync mypy custom_components/battery_notes/ --check-untyped-defs` |
| Fix lint, format, and run mypy | `./scripts/lint` |
| Run tests with coverage | `uv run --no-sync pytest tests --cov=custom_components.battery_notes --cov-report=term-missing --cov-report=html` |
| Validate community library schema | `./scripts/validate_library` |
| Check translation consistency | `uv run --no-sync pytest tests/test_translations.py -v` |
| Preview documentation | `uv run zensical serve` |

`scripts/setup` runs `uv sync`. `scripts/lint` runs Ruff with `--fix`, formats the
whole repository, and then runs mypy; inspect its diff for unrelated changes.
`scripts/validate_library` uses `uvx` to run `check-jsonschema` and can require a
tool download. `.vscode/tasks.json` contains additional development tasks.

For local integration testing, Home Assistant can run from the sibling Core
checkout with this repository's `custom_components/battery_notes` symlinked into
the chosen HA configuration directory's `custom_components` directory. Keep that
development configuration separate from automated tests and out of commits.

## Coding conventions

- Follow Ruff/mypy configuration and surrounding conventions. Prefer typed
  dataclasses for shared runtime data, existing `CONF_*`/`ATTR_*` constants, and
  HA async helpers. Keep blocking file operations off the event loop.
- Use direct access for schema-guaranteed keys; reserve defaults for genuinely
  optional or legacy data. Clearing optional templates and the user-library
  option must work, rather than silently retaining previous values.
- Keep exception scopes narrow and comments focused on non-obvious constraints.
  Existing broad exceptions or lint suppressions are not a reason to add more.
- Check the working-tree diff before finishing. Keep generated artifacts, local
  HA configuration, and unrelated formatting out of the change. Release packaging
  sets the manifest version from the release tag; do not bump it for routine work.

## Related guidance

For regression coverage, read [Tests and validation](testing.md).

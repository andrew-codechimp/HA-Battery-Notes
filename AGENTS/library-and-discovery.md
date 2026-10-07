# Library and discovery

[Back to the instruction index](../AGENTS.md)

Read when changing device definitions, matching, downloads, user libraries, discovery, or generated library documentation.

## Library and discovery

`library/library.json` is the maintained community dataset. Runtime downloads use
the primary and fallback URLs in `const.py`; the library is not embedded as a
Python device list.

- Match manufacturer/model case-insensitively. Optional `model_id`, `hw_version`,
  and `model_match_method` refine matches. Generic fallbacks must not override
  incompatible specific identifiers. Ambiguous conflicting matches return no result.
- User-library records are loaded before community records, but matching still
  applies ambiguity checks; do not assume arbitrary conflicting entries override.
- Invalid individual records are skipped. If no devices can be loaded, retain
  the previously loaded library. Keep loads serialized with the existing lock.
- Downloads share an update lock, validate content, and replace the file through
  a temporary file. Preserve the existing usable file and update timestamp on
  failed downloads; filesystem I/O belongs in executor jobs.
- Discovery creates confirmation flows rather than silently adding notes. It
  accounts for existing notes, related/split devices, ignored entries/domains,
  disabled devices, child/composite devices, and `MANUAL` library definitions.
- Adding or removing a note must not cause repeated downloads or duplicate discovery.

For community data changes:

1. Use manufacturer/model values as HA reports them. Different integration
   spellings may need separate records; do not replace one with another.
2. Omit `battery_quantity` for a single battery; otherwise use an integer greater
   than one. Add model/hardware identifiers only when the source actually reports them.
3. Use `MANUAL` for indistinguishable variants with different batteries, rather
   than introducing conflicting definitions. See `docs/library.md` for conventions.
4. Run `./scripts/validate_library` and
   `uv run --no-sync pytest tests/test_library_data.py tests/test_library.py -v`.
5. `library.md` is generated. If regeneration is required, run
   `uv run --only-group library .github/scripts/library_doc/update_library_files.py`;
   this sorts the dataset and rewrites the table. The librarian workflow also runs
   after library changes reach `main`. Avoid unrelated generated-file churn.

There are schemas at `library/schema.json` and
`custom_components/battery_notes/schema.json`. Review both when changing the
library format: CI validates against the former, while the updater copies the
latter into runtime storage.

## Related guidance

For the parent entry and configuration flows, read [Repository and runtime architecture](architecture.md). For runtime regression coverage, read [Tests and validation](testing.md).

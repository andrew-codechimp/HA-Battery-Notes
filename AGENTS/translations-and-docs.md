# Translations and documentation

[Back to the instruction index](../AGENTS.md)

Read when changing UI strings, action descriptions, translation placeholders, user documentation, or example blueprints.

## Translations and documentation

- `translations/en.json` is the English source for Crowdin. This repository does
  not use a `strings.json` plus Core translation-generation workflow. Update the
  appropriate config, subentry, options, entity, exceptions, repairs, or services
  section directly. Preserve placeholder names across translations.
- Keep English service names/fields aligned with `services.yaml`;
  `test_translations.py` checks that correspondence and translated placeholders.
  Non-English translations are managed through Crowdin; avoid bulk rewrites for
  unrelated feature work.
- Update the relevant `docs/` page when user-visible behavior changes. Check
  example blueprints when changing action/event contracts.

## Related guidance

For action contracts, read [Actions and responses](actions.md). For validation coverage, read [Tests and validation](testing.md).

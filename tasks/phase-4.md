# Phase 4: IPA Enrichment + Translation Stubs

## Goal

Add linguistic enrichment over segmented manifests. After this phase, users can
add French IPA to their study segments, and the translation extension point is
defined without making network calls.

## User-Usable Result

- `uv run audawispr enrich out/segments.json --ipa --output out/enriched.json`
  writes a manifest with IPA values populated for French segments.
- Translation fields exist in the manifest but remain empty in Epic 1.

## TODO

- [ ] Add `epitran` dependency.
- [ ] Add optional `ipa`, `translation`, and `translation_provider` fields to
  manifest segments if they are not already present.
- [ ] Implement French IPA service using Epitran.
- [ ] Implement a language-aware enrichment core that can enrich an in-memory
  manifest and a file-backed manifest.
- [ ] Define `TranslationProvider` interface and provider registry.
- [ ] Implement only the `none` translation provider for Epic 1.
- [ ] Make `deepl` and `openai` accepted CLI option values that fail in core
  with a clean unsupported-provider error before any network access.
- [ ] Add `audawispr enrich` CLI options for input, output, `--ipa`, and
  `--translate`.
- [ ] Add clear errors for unsupported IPA language and unsupported translation
  providers.
- [ ] Update README with `enrich` command usage and Epic 1 translation limits.

## Defaults

- `--translate none`
- IPA is opt-in with `--ipa`.
- French language code is `fr`.
- In Epic 1, untranslated segments store `translation=null` and
  `translation_provider=null`; do not write `"none"` into the manifest provider
  field.

## Acceptance Checks

- [ ] Tests for French IPA enrichment.
- [ ] Tests for unsupported-language IPA errors.
- [ ] Tests that Epitran import or initialization failures produce a clean
  dependency/enrichment error without a traceback.
- [ ] Cross-platform CI covers Epitran import/error-path behavior; any real IPA
  smoke that proves platform-sensitive may be optional outside normal CI.
- [ ] Tests that `--translate none` does not alter translation fields.
- [ ] Tests that CLI `--translate none` maps to manifest `translation=null` and
  `translation_provider=null`.
- [ ] Tests that `deepl` and `openai` fail without network access.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr enrich --help`
- [ ] `uv run audawispr validate out/enriched.json` succeeds for a fixture
  enriched manifest.
- [ ] CI quality workflow passes.
- [ ] README documents Phase 4 command and translation scope.

## Notes

- Do not implement live DeepL or OpenAI calls in this phase.
- Do not implement audio clipping or export in this phase.

## Verification Evidence

- Pending.

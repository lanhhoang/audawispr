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

## Actual Implementation

### Readiness Review

- The repo is ready to start Phase 4 from the current branch:
  `epic-1-phase-4-ipa-enrichment-translation-stubs`.
- Phase 1-3 implementation is present and Phase 3 is merged into `master`.
- Local quality checks passed before replanning:
  - `uv run pytest`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run ty check src tests`
- Current blockers are planning/API details, not broken existing code.

### Replan

- [ ] Expand `TranscriptSegment` with optional `ipa`, `translation`, and
  `translation_provider` fields defaulting to `None`.
- [ ] Keep manifest `schema_version` at `1.0` because enrichment fields are an
  additive optional schema change.
- [ ] Add `EnrichmentError` for expected enrichment failures.
- [ ] Add an enrichment core module with:
  - [ ] `EnrichmentOptions(ipa: bool = False, translation_provider: str = "none")`
  - [ ] `enrich_manifest(manifest, options)` for in-memory use
  - [ ] `enrich_manifest_file(input_path, output_path, options)` for file-backed
    use
- [ ] Add Epitran as a runtime dependency and update `uv.lock`.
- [ ] Implement French IPA with Epitran using audawispr language `fr`, `fr-*`,
  and `fr_*` mapped to Epitran code `fra-Latn`.
- [ ] Raise a clean unsupported-language error for IPA requests outside French.
- [ ] Implement translation stubs only:
  - [ ] `none` performs no network access and leaves translation fields unchanged.
  - [ ] `deepl` fails with a clean unsupported-provider error before output is
    written.
  - [ ] `openai` fails with a clean unsupported-provider error before output is
    written.
- [ ] Add `audawispr enrich MANIFEST --output out/enriched.json --ipa
  --translate none`.
- [ ] Export enrichment APIs from `audawispr.core`.
- [ ] Update README with Phase 4 status, `enrich` usage, French-only IPA scope,
  and Epic 1 translation limits.

### Tests And Verification

- [ ] Test old manifests without enrichment fields still load.
- [ ] Test saved enriched manifests validate and round-trip with null/default
  enrichment fields.
- [ ] Test French segments get non-empty IPA when `--ipa` is enabled.
- [ ] Test unsupported IPA languages fail cleanly.
- [ ] Test simulated Epitran import or initialization failures raise
  `EnrichmentError` without traceback leakage.
- [ ] Test `--translate none` leaves translation fields unchanged.
- [ ] Test `deepl` and `openai` fail without network access or output writes.
- [ ] Test root help lists `enrich`.
- [ ] Test `enrich --help` includes `--output`, `--ipa`, and `--translate`.
- [ ] Run `uv run pytest`.
- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run ruff format --check .`.
- [ ] Run `uv run ty check src tests`.
- [ ] Run `uv run audawispr enrich --help`.
- [ ] Run `uv run audawispr validate out/enriched.json` on an enriched fixture
  or real local output.

### Assumptions

- Phase 4 does not implement live translation, audio clipping, CSV export, or
  APKG export.
- IPA is opt-in.
- Running `enrich` without `--ipa` and with `--translate none` is allowed as a
  schema-normalizing pass.
- Epitran output is accepted as practical IPA for Epic 1, with French as the
  only supported IPA language.

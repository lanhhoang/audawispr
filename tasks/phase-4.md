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

- [x] Add `epitran` dependency.
- [x] Add optional `ipa`, `translation`, and `translation_provider` fields to
  manifest segments if they are not already present.
- [x] Implement French IPA service using Epitran.
- [x] Implement a language-aware enrichment core that can enrich an in-memory
  manifest and a file-backed manifest.
- [x] Define `TranslationProvider` interface and provider registry.
- [x] Implement only the `none` translation provider for Epic 1.
- [x] Make `deepl` and `openai` accepted CLI option values that fail in core
  with a clean unsupported-provider error before any network access.
- [x] Add `audawispr enrich` CLI options for input, output, `--ipa`, and
  `--translate`.
- [x] Add clear errors for unsupported IPA language and unsupported translation
  providers.
- [x] Update README with `enrich` command usage and Epic 1 translation limits.

## Defaults

- `--translate none`
- IPA is opt-in with `--ipa`.
- French language code is `fr`.
- In Epic 1, untranslated segments store `translation=null` and
  `translation_provider=null`; do not write `"none"` into the manifest provider
  field.

## Acceptance Checks

- [x] Tests for French IPA enrichment.
- [x] Tests for unsupported-language IPA errors.
- [x] Tests that Epitran import or initialization failures produce a clean
  dependency/enrichment error without a traceback.
- [ ] Cross-platform CI covers Epitran import/error-path behavior; any real IPA
  smoke that proves platform-sensitive may be optional outside normal CI.
- [x] Tests that `--translate none` does not alter translation fields.
- [x] Tests that CLI `--translate none` maps to manifest `translation=null` and
  `translation_provider=null`.
- [x] Tests that `deepl` and `openai` fail without network access.
- [x] `uv run pytest`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run ty check src tests`
- [x] `uv run audawispr enrich --help`
- [x] `uv run audawispr validate out/enriched.json` succeeds for a fixture
  enriched manifest.
- [ ] CI quality workflow passes.
- [x] README documents Phase 4 command and translation scope.

## Notes

- Do not implement live DeepL or OpenAI calls in this phase.
- Do not implement audio clipping or export in this phase.

## Verification Evidence

- Focused Phase 4 tests passed:
  `uv run pytest tests/test_enrichment.py tests/test_cli.py tests/test_manifest.py tests/test_core_exports.py`
- `uv run pytest` passed with 50 tests.
- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed.
- `uv run ty check src tests` passed.
- `uv run audawispr enrich --help` passed.
- `uv run audawispr enrich out/segments.json --ipa --output out/enriched.json`
  passed against the real local segmented manifest.
- `uv run audawispr validate out/enriched.json` passed.
- Remote CI is pending.

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

- [x] Expand `TranscriptSegment` with optional `ipa`, `translation`, and
  `translation_provider` fields defaulting to `None`.
- [x] Keep manifest `schema_version` at `1.0` because enrichment fields are an
  additive optional schema change.
- [x] Add `EnrichmentError` for expected enrichment failures.
- [x] Add an enrichment core module with:
  - [x] `EnrichmentOptions(ipa: bool = False, translation_provider: str = "none")`
  - [x] `enrich_manifest(manifest, options)` for in-memory use
  - [x] `enrich_manifest_file(input_path, output_path, options)` for file-backed
    use
- [x] Add Epitran as a runtime dependency and update `uv.lock`.
- [x] Implement French IPA with Epitran using audawispr language `fr`, `fr-*`,
  and `fr_*` mapped to Epitran code `fra-Latn`.
- [x] Raise a clean unsupported-language error for IPA requests outside French.
- [x] Implement translation stubs only:
  - [x] `none` performs no network access and leaves translation fields unchanged.
  - [x] `deepl` fails with a clean unsupported-provider error before output is
    written.
  - [x] `openai` fails with a clean unsupported-provider error before output is
    written.
- [x] Add `audawispr enrich MANIFEST --output out/enriched.json --ipa
  --translate none`.
- [x] Export enrichment APIs from `audawispr.core`.
- [x] Update README with Phase 4 status, `enrich` usage, French-only IPA scope,
  and Epic 1 translation limits.

### Tests And Verification

- [x] Test old manifests without enrichment fields still load.
- [x] Test saved enriched manifests validate and round-trip with null/default
  enrichment fields.
- [x] Test French segments get non-empty IPA when `--ipa` is enabled.
- [x] Test unsupported IPA languages fail cleanly.
- [x] Test simulated Epitran import or initialization failures raise
  `EnrichmentError` without traceback leakage.
- [x] Test `--translate none` leaves translation fields unchanged.
- [x] Test `deepl` and `openai` fail without network access or output writes.
- [x] Test root help lists `enrich`.
- [x] Test `enrich --help` includes `--output`, `--ipa`, and `--translate`.
- [x] Run `uv run pytest`.
- [x] Run `uv run ruff check .`.
- [x] Run `uv run ruff format --check .`.
- [x] Run `uv run ty check src tests`.
- [x] Run `uv run audawispr enrich --help`.
- [x] Run `uv run audawispr validate out/enriched.json` on an enriched fixture
  or real local output.

### Assumptions

- Phase 4 does not implement live translation, audio clipping, CSV export, or
  APKG export.
- IPA is opt-in.
- Running `enrich` without `--ipa` and with `--translate none` is allowed as a
  schema-normalizing pass.
- Epitran output is accepted as practical IPA for Epic 1, with French as the
  only supported IPA language.

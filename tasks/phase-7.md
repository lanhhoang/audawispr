# Phase 7: Native `.apkg` Export

## Goal

Add Genanki deck generation with embedded media. After this phase, users can
turn an already-clipped manifest into a ready-to-import Anki package.

## User-Usable Result

- `uv run audawispr export out/clipped.json --output deck.apkg --deck-name "My French Deck"`
  writes a non-empty `.apkg` file with text, audio, IPA, optional translation,
  and source metadata fields.

## TODO

- [ ] Add `genanki` dependency.
- [ ] Extend export format support with `apkg`.
- [ ] Define default deck name, model name, hardcoded deck ID, hardcoded model
  ID, fields, and card template.
- [ ] Add `--deck-name` CLI option while keeping a stable default deck name.
- [ ] Add audio media embedding for each segment with an `audio_file`.
- [ ] Generate stable note GUIDs from SHA-256 text
  `{source_audio.sha256}:{segment.id}` passed through Genanki's GUID helper.
- [ ] Infer `apkg` format when export output path ends in `.apkg`.
- [ ] Keep `anki-csv` behavior from Phase 6 working.
- [ ] Add clear errors for missing snippets, empty decks, invalid output paths,
  and package write failures.

## Defaults

- Deck name: `audawispr::French`
- Deck ID: `2059400110`
- Model name: `audawispr Segment Card`
- Model ID: `2059400111`
- Fields: `SourceText`, `Audio`, `IPA`, `Translation`, `SourceFile`,
  `TimestampRange`, `SegmentId`
- Card front shows source text and audio.
- Card back shows IPA, translation, source file, and timestamp range.
- Stable note identity: source audio hash plus segment ID.
- Audio-only card fronts are out of scope for Epic 1.

## Acceptance Checks

- [x] Tests for `.apkg` file generation.
- [x] Tests for media inclusion.
- [x] CI-friendly APKG generation test using fixture manifests and fixture media.
- [x] Tests for `--deck-name`.
- [x] Tests for card template field mapping.
- [x] Tests for stable note GUIDs.
- [x] Tests for missing or empty audio errors.
- [x] Tests that `anki-csv` export still passes.
- [x] `uv run pytest`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run ty check src tests`
- [x] CI quality workflow passes.
- [x] Manual smoke creates a non-empty `.apkg` from a fixture clipped manifest.
- [x] README documents APKG export and `--deck-name`.

## Notes

- Do not implement the full root one-shot command in this phase.
- Manual Anki Desktop import remains separate from CI and can be tracked as a
  release confidence check.

## Verification Evidence

- `uv run pytest` — 97 passed.
- `uv run ruff check .` — passed.
- `uv run ruff format --check .` — passed.
- `uv run ty check src tests` — passed.
- `uv run audawispr export out/clipped.json --output out/deck.apkg --deck-name "My French Deck"` — produces 110K non-empty `.apkg` file.
- Manual smoke: inspected APKG as ZIP, confirmed `collection.anki2` and `media` entries present.
- SQLite inspection of `collection.anki2` confirms deck name and notes with stable GUIDs.
- CSV export from Phase 6 still works (backward compat verified by tests).
- CI quality workflow passed on remote GitHub Actions (Linux, macOS, Windows).
- Manual Anki Desktop import of `deck.apkg` verified: deck loaded with correct name, cards, audio playback, and fields.

## Actual Implementation

### Design Decision: Dynamic Default Deck Name

The default deck name is `audawispr::{manifest.language}` — constructed from the manifest's
language code at export time. No hardcoded mapping table. Example: `fr` → `audawispr::fr`.
The `--deck-name` CLI option overrides the default.

### Group A: Dependency + Core Export Module

1. **`pyproject.toml`** — add `"genanki>=0.13.1"` to runtime dependencies.
2. **`src/audawispr/core/export.py`**:
   - Add `deck_name: str | None = None` to `ExportOptions`.
   - Add hardcoded constants: `DECK_ID=2059400110`, `MODEL_ID=2059400111`, `MODEL_NAME="audawispr Segment Card"`.
   - Refactor `export_manifest_file()`:
     - If `opts.format == "apkg"` or `output_path.suffix == ".apkg"` → build APKG.
     - Else → existing CSV logic.
   - Add `_export_apkg()` helper:
     - Build `genanki.Model` with 7 fields + card template (front: text+audio,
       back: IPA+translation+source+timestamp).
     - Create `genanki.Deck(name=deck_name or f"audawispr::{manifest.language}", deck_id=DECK_ID)`.
     - For each segment: `Note` subclass with `guid = genanki.guid_for(manifest.source_audio.sha256, segment.id)`.
     - `Package.media_files` = resolved snippet paths.
     - `package.write_to_file(output_path)`.
   - Error handling: missing snippet, empty deck, write failure.
3. **`src/audawispr/core/__init__.py`** — no changes needed (already exports `ExportOptions`, `export_manifest_file`).

### Group B: CLI

1. **`src/audawispr/cli.py`** — `export` command:
   - Add `--deck-name` option.
   - Update `--output` help: "Output directory for CSV/media, or `.apkg` file path."
   - Update `--format` help: mention both `anki-csv` and `apkg`.
   - Pass `deck_name` to `ExportOptions`.

### Group C: Tests

1. **`tests/test_export.py`**:
   - Change `test_export_unsupported_format` to use `"pdf"` instead of `"apkg"`.
   - Add `test_export_apkg_file_created` — non-empty `.apkg` exists.
   - Add `test_export_apkg_media_included` — inspect `.apkg` as ZIP.
   - Add `test_export_apkg_deck_name` — custom `--deck-name` reflected.
   - Add `test_export_apkg_default_deck_name` — falls back to `audawispr::fr`.
   - Add `test_export_apkg_card_template` — verify front/back fields.
   - Add `test_export_apkg_stable_guid` — deterministic reruns.
   - Add `test_export_apkg_missing_snippet_error` — clear error.
   - Add `test_export_apkg_empty_manifest_error` — no segments.
   - Add `test_export_infer_apkg_from_path` — `--output deck.apkg` infers format.
2. **`tests/test_cli.py`** — add export CLI tests for `--deck-name`, `--format apkg`, and format inference.

### Group D: Documentation

1. **`README.md`** — add APKG export section.
2. **`tasks/phase-7.md`** — update acceptance checks and verification evidence after CI.

### Execution Order

```
1. Group A (dependency + core) → uv run pytest
2. Group B (CLI)               → uv run pytest
3. Group C (tests)             → uv run pytest
4. Group D (docs)              → uv run ruff check . && uv run ruff format --check . && uv run ty check src tests && uv run pytest
5. Push, wait for CI, update phase-7.md
```

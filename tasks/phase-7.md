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
- [ ] Generate stable note GUIDs from source audio hash plus segment ID.
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

## Acceptance Checks

- [ ] Tests for `.apkg` file generation.
- [ ] Tests for media inclusion.
- [ ] CI-friendly APKG generation test using fixture manifests and fixture media.
- [ ] Tests for `--deck-name`.
- [ ] Tests for card template field mapping.
- [ ] Tests for stable note GUIDs.
- [ ] Tests for missing or empty audio errors.
- [ ] Tests that `anki-csv` export still passes.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] CI quality workflow passes.
- [ ] Manual smoke creates a non-empty `.apkg` from a fixture clipped manifest.

## Notes

- Do not implement the full root one-shot command in this phase.
- Manual Anki Desktop import remains separate from CI and can be tracked as a
  release confidence check.

## Verification Evidence

- Pending.

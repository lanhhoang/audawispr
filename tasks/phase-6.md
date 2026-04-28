# Phase 6: Importable Anki CSV Export

## Goal

Add a useful pre-APKG export target that creates Anki-compatible rows and media
files. After this phase, users can manually import cards into Anki without
waiting for native `.apkg` support.

## User-Usable Result

- `uv run audawispr export out/clipped.json --format anki-csv --output out/anki-csv`
  writes an Anki-compatible CSV and a media directory.

## TODO

- [ ] Add export options and result types for file-backed and in-memory
  manifest export.
- [ ] Implement media resolution and deterministic media copying for segment
  snippets.
- [ ] Implement `anki-csv` writer with stable field order.
- [ ] Include source text, audio reference, IPA, translation, source filename,
  timestamp range, and segment ID fields.
- [ ] Add `audawispr export` CLI with `--format anki-csv` and output path.
- [ ] Add clear errors for missing audio files, unsupported formats, and invalid
  manifests.
- [ ] Preserve manifest-driven reruns without retranscription, segmentation, or
  clipping.

## Defaults

- CSV field order:
  `SourceText`, `Audio`, `IPA`, `Translation`, `SourceFile`,
  `TimestampRange`, `SegmentId`.
- Copied media goes under the export output directory.

## Acceptance Checks

- [ ] Tests for field order and row values.
- [ ] Tests for media copying and audio references.
- [ ] Tests for missing snippet errors.
- [ ] Tests for deterministic reruns.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr export --help`

## Notes

- Do not implement native `.apkg` export in this phase.
- The CSV should be usable for manual Anki import with media copied alongside
  it.

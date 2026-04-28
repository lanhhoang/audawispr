# Phase 6: Importable Anki CSV Export

## Goal

Add a useful pre-APKG export target that creates Anki-compatible rows and media
files. After this phase, users can manually import cards into Anki without
waiting for native `.apkg` support.

## User-Usable Result

- `uv run audawispr export out/clipped.json --format anki-csv --output out/anki-csv`
  writes `out/anki-csv/cards.csv` and `out/anki-csv/media/`.

## TODO

- [ ] Add export options and result types for file-backed and in-memory
  manifest export.
- [ ] Implement media resolution and deterministic media copying for segment
  snippets.
- [ ] Implement `anki-csv` writer at `cards.csv` with stable field order.
- [ ] Write CSV with UTF-8 encoding and Python `csv` newline handling to avoid
  platform-specific line ending bugs.
- [ ] Include source text, audio reference, IPA, translation, source filename,
  timestamp range, and segment ID fields.
- [ ] Write audio references in Anki sound syntax, such as
  `[sound:0001_seg-0001.mp3]`.
- [ ] Document manual import expectations in README, including how copied media
  should be made available to Anki.
- [ ] Add `audawispr export` CLI with `--format anki-csv` and output path.
- [ ] Add clear errors for missing audio files, unsupported formats, and invalid
  manifests.
- [ ] Preserve manifest-driven reruns without retranscription, segmentation, or
  clipping.

## Defaults

- CSV field order:
  `SourceText`, `Audio`, `IPA`, `Translation`, `SourceFile`,
  `TimestampRange`, `SegmentId`.
- Copied media goes under `<output>/media/`.
- Audio references in CSV use media basenames only, not OS-specific paths.

## Acceptance Checks

- [ ] Tests for field order and row values.
- [ ] Tests for media copying and audio references.
- [ ] Tests for `[sound:...]` syntax.
- [ ] Tests for UTF-8 text and newline-safe CSV output.
- [ ] Tests for missing snippet errors.
- [ ] Tests for deterministic reruns.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr export --help`
- [ ] CI quality workflow passes.

## Notes

- Do not implement native `.apkg` export in this phase.
- The CSV should be usable for manual Anki import with media copied alongside
  it.

## Verification Evidence

- Pending.

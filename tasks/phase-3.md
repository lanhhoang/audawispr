# Phase 3: Sentence Segmentation + Inspection TSV

## Goal

Add timestamp-aware segmentation from transcription manifests. After this phase,
users can produce cleaner sentence-like learning units and inspect them in a TSV
before any audio clipping or Anki export exists.

## User-Usable Result

- `uv run audawispr segment out/transcript.json --output out/segments.json`
  writes a segmented manifest.
- An inspection TSV is written next to the output manifest unless an explicit TSV
  path is provided.

## TODO

- [ ] Implement segmentation options for pause threshold, minimum duration,
  maximum duration, and short-segment merging.
- [ ] Segment from manifest word timestamps using punctuation, pauses, and
  duration bounds.
- [ ] Preserve source audio metadata and transcription settings in the output
  manifest.
- [ ] Rebuild segment IDs, indexes, text, start/end timestamps, and word lists
  for each segmented unit.
- [ ] Add inspection TSV writer with id, index, start/end timestamps, and text.
- [ ] Add `audawispr segment` CLI with output and inspection TSV options.
- [ ] Add clear errors for manifests with no word timestamps, invalid options,
  invalid timestamps, and validation failure.
- [ ] Update README with `segment` command usage and inspection TSV behavior.

## Defaults

- Split on sentence punctuation and pauses.
- `pause_split_ms=700`
- `min_duration_ms=600`
- `max_duration_ms=7000`
- `merge_short=true`

## Acceptance Checks

- [ ] Tests for punctuation splits.
- [ ] Tests for pause splits.
- [ ] Tests for max-duration splits.
- [ ] Tests for short-segment merging.
- [ ] Tests for invalid or missing word timestamps.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr segment --help`
- [ ] `uv run audawispr validate out/segments.json` succeeds for a fixture
  segmented manifest.
- [ ] CI quality workflow passes.
- [ ] README documents Phase 3 command.

## Notes

- Do not implement IPA, clipping, or export in this phase.
- The TSV is inspection-only in Epic 1. Do not implement TSV edit import/apply
  behavior in this phase.
- The segmented manifest should remain valid input for later enrichment and
  clipping phases.

## Verification Evidence

- Pending.

## Actual Implementation

Phase 3 is ready to execute from a clean baseline: Phase 1 and Phase 2 are
merged, this branch is clean, and the current quality checks pass locally.
Before implementation, make the plan more concrete so segmentation behavior,
TSV output, and CLI options are deterministic.

### Implementation TODO

- [ ] Add a reusable segmentation core module with `SegmentationOptions` and
  `segment_manifest(manifest, options)`.
- [ ] Add `SegmentationError` under core errors and route expected failures
  through the existing CLI error handling path.
- [ ] Export the Phase 3 segmentation API from `audawispr.core`.
- [ ] Keep the manifest schema unchanged: preserve `language`, `source_audio`,
  and `transcription`, then rebuild only `segments`.
- [ ] Rebuild segmented units with deterministic ids, indexes, timestamps,
  text, and word lists.
- [ ] Flatten words in timestamp order and split on terminal punctuation,
  pauses, and maximum duration.
- [ ] Apply soft punctuation/pause splits only after `min_duration_ms`; apply
  `max_duration_ms` as a hard split.
- [ ] Merge short segments with the next segment when possible, otherwise with
  the previous segment when `merge_short` is enabled.
- [ ] Use defaults `pause_split_ms=700`, `min_duration_ms=600`,
  `max_duration_ms=7000`, and `merge_short=true`.
- [ ] Add an atomic inspection TSV writer with columns `id`, `index`, `start`,
  `end`, and `text`.
- [ ] Default the TSV path to the output manifest path with a `.tsv` suffix,
  unless `--inspection-tsv PATH` is provided.
- [ ] Add `audawispr segment MANIFEST --output out/segments.json` with
  `--inspection-tsv`, `--pause-split-ms`, `--min-duration-ms`,
  `--max-duration-ms`, and `--merge-short/--no-merge-short`.
- [ ] Validate option ranges and return clear errors for invalid manifests,
  missing or unusable word timestamps, invalid timestamps, invalid options, and
  output write failures.
- [ ] Update `README.md` status, segment command usage, and inspection TSV
  behavior.

### Test TODO

- [ ] Add core tests for punctuation splits.
- [ ] Add core tests for pause splits.
- [ ] Add core tests for maximum-duration splits.
- [ ] Add core tests for short-segment merging.
- [ ] Add core tests for invalid options and invalid word timestamp inputs.
- [ ] Add tests proving the segmented output is still a valid
  `TranscriptManifest`.
- [ ] Add TSV tests for header, row shape, default path behavior, and explicit
  TSV path behavior.
- [ ] Add CLI tests for `segment --help`, successful JSON/TSV writes, invalid
  manifests, and invalid options.
- [ ] Run `uv run pytest`.
- [ ] Run `uv run ruff check .`.
- [ ] Run `uv run ruff format --check .`.
- [ ] Run `uv run ty check src tests`.
- [ ] Run `uv run audawispr segment --help`.
- [ ] Run `uv run audawispr validate <fixture-segments.json>` against a
  generated segmented manifest.

### Out Of Scope

- [ ] Do not implement IPA, translation, clipping, CSV export, APKG export, or
  TSV edit-import in Phase 3.
- [ ] Do not add new runtime dependencies unless implementation proves the
  standard library and current dependencies are insufficient.

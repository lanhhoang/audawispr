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

- [x] Implement segmentation options for pause threshold, minimum duration,
  maximum duration, and short-segment merging.
- [x] Segment from manifest word timestamps using punctuation, pauses, and
  duration bounds.
- [x] Preserve source audio metadata and transcription settings in the output
  manifest.
- [x] Rebuild segment IDs, indexes, text, start/end timestamps, and word lists
  for each segmented unit.
- [x] Add inspection TSV writer with id, index, start/end timestamps, and text.
- [x] Add `audawispr segment` CLI with output and inspection TSV options.
- [x] Add clear errors for manifests with no word timestamps, invalid options,
  invalid timestamps, and validation failure.
- [x] Update README with `segment` command usage and inspection TSV behavior.

## Defaults

- Split on sentence punctuation and pauses.
- `pause_split_ms=700`
- `min_duration_ms=600`
- `max_duration_ms=7000`
- `merge_short=true`

## Acceptance Checks

- [x] Tests for punctuation splits.
- [x] Tests for pause splits.
- [x] Tests for max-duration splits.
- [x] Tests for short-segment merging.
- [x] Tests for invalid or missing word timestamps.
- [x] `uv run pytest`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run ty check src tests`
- [x] `uv run audawispr segment --help`
- [x] `uv run audawispr validate out/segments.json` succeeds for a fixture
  segmented manifest.
- [ ] CI quality workflow passes.
- [x] README documents Phase 3 command.

## Notes

- Do not implement IPA, clipping, or export in this phase.
- The TSV is inspection-only in Epic 1. Do not implement TSV edit import/apply
  behavior in this phase.
- The segmented manifest should remain valid input for later enrichment and
  clipping phases.

## Verification Evidence

- `uv run pytest` passed with 37 tests.
- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed.
- `uv run ty check src tests` passed.
- `uv run audawispr segment --help` passed.
- `uv run audawispr segment /tmp/audawispr-phase3-transcript.json --output
  /tmp/audawispr-phase3-segments.json` passed.
- `uv run audawispr validate /tmp/audawispr-phase3-segments.json` passed.
- Remote CI is pending.

## Actual Implementation

Phase 3 is ready to execute from a clean baseline: Phase 1 and Phase 2 are
merged, this branch is clean, and the current quality checks pass locally.
Before implementation, make the plan more concrete so segmentation behavior,
TSV output, and CLI options are deterministic.

### Implementation TODO

- [x] Add a reusable segmentation core module with `SegmentationOptions` and
  `segment_manifest(manifest, options)`.
- [x] Add `SegmentationError` under core errors and route expected failures
  through the existing CLI error handling path.
- [x] Export the Phase 3 segmentation API from `audawispr.core`.
- [x] Keep the manifest schema unchanged: preserve `language`, `source_audio`,
  and `transcription`, then rebuild only `segments`.
- [x] Rebuild segmented units with deterministic ids, indexes, timestamps,
  text, and word lists.
- [x] Flatten words in timestamp order and split on terminal punctuation,
  pauses, and maximum duration.
- [x] Apply soft punctuation/pause splits only after `min_duration_ms`; apply
  `max_duration_ms` as a hard split.
- [x] Merge short segments with the next segment when possible, otherwise with
  the previous segment when `merge_short` is enabled.
- [x] Use defaults `pause_split_ms=700`, `min_duration_ms=600`,
  `max_duration_ms=7000`, and `merge_short=true`.
- [x] Add an atomic inspection TSV writer with columns `id`, `index`, `start`,
  `end`, and `text`.
- [x] Default the TSV path to the output manifest path with a `.tsv` suffix,
  unless `--inspection-tsv PATH` is provided.
- [x] Add `audawispr segment MANIFEST --output out/segments.json` with
  `--inspection-tsv`, `--pause-split-ms`, `--min-duration-ms`,
  `--max-duration-ms`, and `--merge-short/--no-merge-short`.
- [x] Validate option ranges and return clear errors for invalid manifests,
  missing or unusable word timestamps, invalid timestamps, invalid options, and
  output write failures.
- [x] Update `README.md` status, segment command usage, and inspection TSV
  behavior.

### Test TODO

- [x] Add core tests for punctuation splits.
- [x] Add core tests for pause splits.
- [x] Add core tests for maximum-duration splits.
- [x] Add core tests for short-segment merging.
- [x] Add core tests for invalid options and invalid word timestamp inputs.
- [x] Add tests proving the segmented output is still a valid
  `TranscriptManifest`.
- [x] Add TSV tests for header, row shape, default path behavior, and explicit
  TSV path behavior.
- [x] Add CLI tests for `segment --help`, successful JSON/TSV writes, invalid
  manifests, and invalid options.
- [x] Run `uv run pytest`.
- [x] Run `uv run ruff check .`.
- [x] Run `uv run ruff format --check .`.
- [x] Run `uv run ty check src tests`.
- [x] Run `uv run audawispr segment --help`.
- [x] Run `uv run audawispr validate <fixture-segments.json>` against a
  generated segmented manifest.

### Out Of Scope

- [x] Do not implement IPA, translation, clipping, CSV export, APKG export, or
  TSV edit-import in Phase 3.
- [x] Do not add new runtime dependencies unless implementation proves the
  standard library and current dependencies are insufficient.

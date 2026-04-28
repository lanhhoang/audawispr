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

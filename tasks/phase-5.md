# Phase 5: Audio Snippet Clipping

## Goal

Add FFmpeg-based snippet generation from segmented or enriched manifests. After
this phase, users can create and listen to clean per-segment audio files before
any Anki export is implemented.

## User-Usable Result

- `uv run audawispr clip out/enriched.json --output-dir out/media` writes audio
  snippets.
- The output manifest is updated with `audio_file` values for each segment.

## TODO

- [ ] Implement FFmpeg/FFprobe resolution shared with `doctor`.
- [ ] Implement clip options for padding before, padding after, format, bitrate,
  force regeneration, and FFmpeg preference.
- [ ] Generate stable snippet filenames from segment index and segment ID.
- [ ] Clip source audio by segment timestamp with configured padding.
- [ ] Reuse existing non-empty snippets unless `--force` is set.
- [ ] Write updated manifest with relative audio paths.
- [ ] Add `audawispr clip` CLI with input manifest, output directory, manifest
  output path, padding, format, bitrate, and force options.
- [ ] Add clear errors for missing source audio, missing FFmpeg, invalid ranges,
  empty generated snippets, and invalid options.

## Defaults

- `audio_format=mp3`
- `bitrate=128k`
- `padding_before_ms=150`
- `padding_after_ms=250`
- Reuse snippets unless `--force` is set.

## Acceptance Checks

- [ ] Synthetic audio clipping test when FFmpeg is available.
- [ ] Tests for stable snippet filenames.
- [ ] Tests for padding bounded by audio duration.
- [ ] Tests for reuse and force regeneration.
- [ ] Tests for missing FFmpeg error behavior.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr clip --help`

## Notes

- Do not implement Anki export in this phase.
- Snippet paths must be suitable for later CSV and APKG export.

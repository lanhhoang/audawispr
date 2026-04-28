# Phase 5: Audio Snippet Clipping

## Goal

Add FFmpeg-based snippet generation from segmented or enriched manifests. After
this phase, users can create and listen to clean per-segment audio files before
any Anki export is implemented.

## User-Usable Result

- `uv run audawispr clip out/enriched.json --output out/clipped.json --output-dir out/media`
  writes audio snippets.
- `out/clipped.json` is written with `audio_file` values for each segment.

## TODO

- [ ] Implement FFmpeg/FFprobe resolution shared with `doctor`.
- [ ] Implement clip options for padding before, padding after, format, bitrate,
  force regeneration, and FFmpeg preference.
- [ ] Generate stable snippet filenames with pattern
  `{index:04d}_{safe_segment_id}.{extension}`.
- [ ] Define `safe_segment_id` as ASCII letters/digits/underscore/dot/hyphen
  only, replacing other characters with `-`, trimming leading/trailing `.-`,
  truncating to 80 characters, and using `segment` if empty.
- [ ] Clip source audio by segment timestamp with configured padding.
- [ ] Invoke FFmpeg with `subprocess.run([...], shell=False)` to keep quoting
  and execution safe across macOS, Linux, and Windows.
- [ ] Reuse existing non-empty snippets unless `--force` is set.
- [ ] Write updated manifest with relative POSIX-style audio paths.
- [ ] Add `audawispr clip` CLI with input manifest, output directory, manifest
  output path, padding, format, bitrate, and force options.
- [ ] Add clear errors for missing source audio, missing FFmpeg, invalid ranges,
  empty generated snippets, and invalid options.
- [ ] Update README with `clip` command usage.

## Defaults

- `audio_format=mp3`
- `bitrate=128k`
- `padding_before_ms=150`
- `padding_after_ms=250`
- Reuse snippets unless `--force` is set.
- `--output` is required; clipping must not modify the input manifest in place
  unless a later plan explicitly adds an in-place mode.
- Snippet filename example: `0001_seg-0001.mp3`.
- Use available FFmpeg/FFprobe binaries from `AUDAWISPR_FFMPEG`,
  `AUDAWISPR_FFPROBE`, `PATH`, or static-ffmpeg. Do not add managed FFmpeg
  installation in this phase.
- Use `Path` internally, but serialize manifest `audio_file` values with `/`
  separators on every OS.

## Acceptance Checks

- [ ] Synthetic audio clipping test when FFmpeg is available.
- [ ] CI always runs no-FFmpeg and FFmpeg error-path tests; real clipping tests
  may be skipped when FFmpeg is unavailable.
- [ ] Tests for stable snippet filenames.
- [ ] Tests for `safe_segment_id` replacement, trimming, truncation, and empty
  fallback.
- [ ] Tests for padding bounded by audio duration.
- [ ] Tests for POSIX-style serialized `audio_file` values on Windows-style
  paths.
- [ ] Tests for reuse and force regeneration.
- [ ] Tests for missing FFmpeg error behavior.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr clip --help`
- [ ] `uv run audawispr validate out/clipped.json` succeeds for a fixture
  clipped manifest.
- [ ] CI quality workflow passes.
- [ ] README documents Phase 5 command.

## Notes

- Do not implement Anki export in this phase.
- Snippet paths must be suitable for later CSV and APKG export.
- Store `audio_file` paths relative to the clipped manifest location using `/`
  separators, even on Windows.

## Verification Evidence

- Pending.

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

---

## Actual Implementation

### Prerequisite Check

The following are already implemented and do NOT need to be redone:

- `src/audawispr/core/diagnostics.py`: `find_media_tool()` already resolves FFmpeg/FFprobe from `AUDAWISPR_FFMPEG`, `AUDAWISPR_FFPROBE`, `PATH`, and static-ffmpeg.
- `src/audawispr/core/manifest.py`: `TranscriptSegment` already has `audio_file: str | None = None`.
- `src/audawispr/core/errors.py`: Already has `AudawisprError` base class.
- CLI pattern, atomic writes, `ty` config, and CI workflow are already in place.

### Implementation Steps

#### 1. `src/audawispr/core/errors.py`

Add `ClippingError` after the existing error classes.

#### 2. `src/audawispr/core/clipping.py` (new file)

Implement:

- **`ClipOptions`** dataclass (frozen):
  - `padding_before_ms: int = 150`
  - `padding_after_ms: int = 250`
  - `audio_format: str = "mp3"`
  - `bitrate: str = "128k"`
  - `force: bool = False`

- **`safe_segment_id(segment_id: str) -> str`**:
  - Keep ASCII letters, digits, underscore, dot, hyphen only.
  - Replace all other characters with `-`.
  - Strip leading `.` and `-` and `.-` combos.
  - Truncate to 80 characters.
  - Return `"segment"` if result is empty.

- **`stable_snippet_filename(index: int, segment_id: str, extension: str) -> str`**:
  - Format: `f"{index:04d}_{safe_segment_id(segment_id)}.{extension}"`

- **`clip_manifest_file(input_manifest: Path, output_manifest: Path, output_dir: Path, options: ClipOptions) -> TranscriptManifest`**:
  1. Load input manifest.
  2. Resolve source audio path from `manifest.source_audio.path`.
  3. Find FFmpeg via `find_media_tool("ffmpeg", FFMPEG_ENV)`. Raise `ClippingError` if unavailable.
  4. Ensure `output_dir` exists.
  5. For each segment (indexed), compute padded start/end bounded by `source_audio.duration_seconds` (use segment bounds if duration unknown).
  6. If `force=False` and snippet file exists with non-zero size, skip FFmpeg call.
  7. Run FFmpeg with `subprocess.run([...], shell=False)`:
     ```
     ffmpeg -y -ss <padded_start> -t <duration> -i <source_audio>
            -b:a <bitrate> <output_snippet>
     ```
     Use `-y` to overwrite existing files when `force=True`.
  8. Validate snippet was created with non-zero size. Raise `ClippingError` if empty.
  9. Compute `audio_file` as path relative to `output_manifest.parent` using POSIX `/` separators.
  10. Update each segment's `audio_file` field.
  11. Save manifest atomically to `output_manifest`.
  12. Return the saved manifest.

- **`_bounded_time(base: float, padding: float, min_val: float, max_val: float | None) -> float`**:
  - Clamp `base - padding` to `min_val` and `max_val`.

#### 3. `src/audawispr/core/__init__.py`

Add exports:

```python
from audawispr.core.clipping import ClipOptions, clip_manifest_file
```

#### 4. `src/audawispr/cli.py`

Add `clip` command:

```python
@app.command()
def clip(
    manifest: Annotated[Path, typer.Argument(...)],
    output: Annotated[Path, typer.Option("--output", "-o", ...)],
    output_dir: Annotated[Path, typer.Option("--output-dir", ...)],
    padding_before_ms: Annotated[int, typer.Option(...)] = 150,
    padding_after_ms: Annotated[int, typer.Option(...)] = 250,
    audio_format: Annotated[str, typer.Option(...)] = "mp3",
    bitrate: Annotated[str, typer.Option(...)] = "128k",
    force: Annotated[bool, typer.Option("--force", ...)] = False,
) -> None:
    """Clip audio snippets from a segmented or enriched manifest."""
```

Error handling via `_fail()` for `ClippingError`.

#### 5. `tests/test_clipping.py` (new file)

- `test_safe_segment_id_keeps_valid_chars`
- `test_safe_segment_id_replaces_invalid_chars_with_dash`
- `test_safe_segment_id_trims_leading_dots_and_dashes`
- `test_safe_segment_id_truncates_to_80_chars`
- `test_safe_segment_id_falls_back_to_segment`
- `test_stable_snippet_filename`
- `test_clip_manifest_skips_existing_snippets_without_force` (mock FFmpeg, check it is not called)
- `test_clip_manifest_calls_ffmpeg_with_force` (mock FFmpeg, check it is called)
- `test_clip_manifest_raises_when_ffmpeg_missing` (mock `find_media_tool` to return unavailable)
- `test_clip_manifest_raises_when_source_audio_missing`
- `test_clip_manifest_raises_when_snippet_empty` (mock FFmpeg to write empty file)
- `test_clip_manifest_padding_bounded_by_duration` (mock duration_seconds)
- `test_audio_file_paths_are_posix_style_on_windows` (mock `source_audio.path` with backslashes)
- `test_clip_manifest_with_synthetic_audio` (real FFmpeg via `ffmpeg -f lavfi -i anullsrc` - skip if FFmpeg unavailable)

#### 6. `tests/test_cli.py`

Add:

- `test_clip_help_displays_phase_5_options`
- `test_clip_writes_manifest_with_audio_files` (mock `clip_manifest_file`)
- `test_clip_reports_clamping_error`

#### 7. `tests/test_core_exports.py`

Add:

```python
from audawispr.core import ClipOptions, clip_manifest_file
```

#### 8. `README.md`

Add section after `enrich`:

````markdown
Clip audio snippets from a segmented manifest:

```sh
uv run audawispr clip out/enriched.json --output out/clipped.json --output-dir out/media
```
````

#### 9. `tasks/epic-1.md`

- Update Phase 5 row to: `⏳ Pending, need CI status confirmation`
- Leave Epic TODO checkbox unchecked (or mark as `pending CI confirmation`)

### Notes for Implementation

- Use `subprocess.run` with `shell=False` on all platforms.
- `FFMPEG_ENV = "AUDAWISPR_FFMPEG"` (already defined in `diagnostics.py`).
- Synthesize test audio with `ffmpeg -f lavfi -i anullsrc=r=44100:cl=mono -t 5 <temp_file>`.
- Skip synthetic audio tests when `find_media_tool("ffmpeg", FFMPEG_ENV).available` is `False`.
- On Windows, `Path("foo/bar").as_posix()` returns `foo/bar`; use this for serializing `audio_file` values even when `Path` objects use backslash internally.
- Padding bounds: start cannot go below `0`, end cannot exceed `source_audio.duration_seconds` (if known).

### Completion Criteria

Phase 5 is only considered fully complete when the remote GitHub Actions CI workflow passes. Do not mark Phase 5 as "Done" in `tasks/epic-1.md` after local implementation — the epic tracker will be updated manually after CI validation.

# Phase 10: Correctness & Polish

## Goal

Address correctness issues in segmentation, manifest validation, and export; add
resource safeguards; and apply code quality improvements across the remaining
files before v0.1.0 release.

## User-Usable Result

- French text preserves typographic spacing rules.
- SHA-256 fields in manifests are validated for hex content.
- Large audio files are rejected early with a clear message.
- FFmpeg processes include `-nostdin` for reliability.
- Error messages are accurate and actionable.

## TODO

### Group D — `segmentation.py`, `manifest.py`, `export.py`

- [ ] D1: Make `SPACE_BEFORE_RE` language-aware — preserve space before `?`, `!`, `:`, `;` for French; keep no-space for `,`, `.` in all languages
- [ ] D2: Add hex-character validation on `SourceAudio.sha256` field (regex `^[a-f0-9]{64}$`) or Pydantic `model_validator`
- [ ] D3: Log each individual segment skipped in APKG export due to missing `audio_file` (not just error when all missing)
- [ ] D4: Split `ManifestError` catch from `EnrichmentError` in pipeline error handling — provide accurate hints (disk space vs enrichment config)

### Group E — scattered hardening

- [ ] E1: Add `-nostdin` flag to FFmpeg subprocess args in `clip_manifest_file`
- [ ] E2: Validate `bitrate` against regex `^\d+[kM]?$` before passing to FFmpeg
- [ ] E3: Add `MAX_AUDIO_SIZE` guard (5 GB) in `_validate_audio_path` or early in pipeline
- [ ] E4: Add `shutil.disk_usage()` pre-flight check on work directory volume
- [ ] E5: Add `from __future__ import annotations` to `cli.py`, `clipping.py`, `errors.py` for consistency with rest of codebase
- [ ] E6: Narrow `except Exception` to `except ImportError` in `diagnostics.py:_find_static_ffmpeg_tool`
- [ ] E7: Document WhisperModel re-load limitation in transcription module docstring
- [ ] E8: Document `_VERBOSE` module-level global as acceptable for single-invocation CLI
- [ ] E9: Add `-nostdin` also to FFmpeg/FFprobe calls in `diagnostics.py` for CI reliability

## Defaults

- `MAX_AUDIO_SIZE = 5 * 1024 * 1024 * 1024` (5 GB).
- `bitrate` regex allows formats: `128k`, `192k`, `320k`, `1M`, etc.
- French punctuation rule applies when `language` field matches `fr`
  (case-insensitive).
- SHA-256 hex validation uses `model_validator` for clean error messages.
- `from __future__ import annotations` enables PEP 604 syntax (`X | Y`) in all
  files.

## Acceptance Checks

- [ ] French `"Bonjour !"` does not become `"Bonjour!"` (space preserved before `!`)
- [ ] English `"Hello."` remains `"Hello."` (no space before `.` — unchanged behavior)
- [ ] `sha256` field rejects strings with non-hex characters (e.g., `"zzz...z"`)
- [ ] APKG export warns for each segment without audio (not just total failure)
- [ ] `ManifestError` during enrichment shows disk-space hint, not enrichment config hint
- [ ] FFmpeg subprocess includes `-nostdin` in arguments list
- [ ] `bitrate="abc"` raises clear validation error
- [ ] >5 GB audio file raises `InputAudioError` with size message
- [ ] Disk-full scenario raises clear error before pipeline starts
- [ ] `from __future__ import annotations` present in `cli.py`, `clipping.py`, `errors.py`
- [ ] `_find_static_ffmpeg_tool` only catches `ImportError`, not broad `Exception`
- [ ] `diagnostics.py` FFprobe/FFmpeg calls include `-nostdin`

## Verification Evidence

(to be filled after implementation)

## Notes

- Language detection for French punctuation uses the `language` key from
  `TranscriptManifest.source_audio.language`.
- D1 is the only regression fix in this phase; all others are hardening.
- E7 and E8 are documentation-only changes (no code modifications).
- E9 is parity with E1 — same `-nostdin` pattern for ffprobe calls in
  `diagnostics.py:audit_tools`, `_probe_ffprobe_availability`,
  `_status_for_path`, and any other `subprocess.run` calls to ffprobe/ffmpeg.

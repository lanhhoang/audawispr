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

### Group F — Phase 9 residual hardening

- [ ] F1: Unicode-safe whitespace stripping in `_safe_csv_cell` — replace `str.lstrip()` with `re.sub(r'^\s+', '', value)` for Unicode-aware CSV formula injection defense (Python 3.11 `lstrip()` only strips ASCII whitespace; `\u00a0=2+2` bypasses the check)
- [ ] F2: Add `\r` bypass regression test to `test_safe_csv_cell_whitespace_bypass`
- [ ] F3: Add Unicode whitespace test to `_safe_csv_cell` tests
- [ ] F4: In `_has_symlink()` cleanup path (pipeline.py), manually unlink detected symlinks before `shutil.rmtree` on all Python versions instead of just logging a warning
- [ ] F5: Fix or remove `test_rmtree_follow_symlinks_false` — test asserts `follow_symlinks=False` was passed but production code never uses this parameter

## Defaults

- `MAX_AUDIO_SIZE = 5 * 1024 * 1024 * 1024` (5 GB).
- `bitrate` regex allows formats: `128k`, `192k`, `320k`, `1M`, etc.
- French punctuation rule applies when `language` field matches `fr`
  (case-insensitive).
- SHA-256 hex validation uses `model_validator` for clean error messages.
- `from __future__ import annotations` enables PEP 604 syntax (`X | Y`) in all
  files.
- Unicode-safe whitespace stripping uses `re.sub(r'^\s+', '', value)` which handles Python 3.11's ASCII-only `lstrip()` limitation.

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
- [ ] `_safe_csv_cell("\u00a0=2+2")` returns `"'\u00a0=2+2"` (Unicode non-breaking space bypass fixed)
- [ ] `_safe_csv_cell("\r=CMD")` has a regression test
- [ ] `_has_symlink()` unlinks detected symlinks before `shutil.rmtree` proceeds
- [ ] `test_rmtree_follow_symlinks_false` is removed or correctly asserts the actual behavior

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
- F1–F5 are Phase 9 residual findings — medium/low severity issues that were identified during the Phase 9 code review but are not show-stoppers for v0.1.0. They should be fixed before any feature that accepts arbitrary user-provided text into CSV cells.
- F1 (Unicode CSV bypass) becomes more important if custom translations or user-supplied segment IDs are added.

## Actual Implementation

### Execution Groups (by complexity, ascending)

| Group | Tier | Items | Description |
|-------|------|-------|-------------|
| G1 | Trivial | E5, E7, E8, E6 | Docs/imports — `from __future__ import annotations`, docstrings, narrow exception |
| G2 | Simple | E1, E9, D2, E2, E3 | 1–8 line additions — `-nostdin` flags, SHA-256 validator, bitrate regex, MAX_AUDIO_SIZE |
| G3 | Small logic | F1, E4 | Unicode-safe `lstrip` in `_safe_csv_cell`, disk-space pre-flight |
| G4 | Medium logic | D3, D4, F4 | Per-segment audio warnings, split ManifestError hints, manual symlink unlink |
| G5 | Tests | F2, F3, F5 | Regression test for `\r` bypass, Unicode whitespace test, rewrite symlink test |
| G6 | Complex | D1 | Language-aware `SPACE_BEFORE_RE` — plumb `language` through call chain |
| Verify | Gate | pytest, ruff, ty check | Full test suite, lint, format check, typecheck |

### Dependencies

- F2, F3 depend on F1 (G3 → G5)
- F5 depends on F4 (G4 → G5)
- All other items are independent within their group

### Execution Order

G1 → G2 → G3 → G4 → G5 → G6 → Verify

### Decision Log

1. **E4 disk_usage threshold**: 500 MB minimum free space (configurable constant)
2. **D3 skip vs abort**: `_resolve_audio` file-not-found becomes warning + skip per-segment; bulk `audio_count == 0` error still fires if ALL segments missing
3. **D1 `%` character for French**: Space before `%` preserved for French (correct typography); not explicitly required by spec but consistent with French spacing rules

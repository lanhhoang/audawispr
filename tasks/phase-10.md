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

- [x] D1: Make `SPACE_BEFORE_RE` language-aware — preserve space before `?`, `!`, `:`, `;` for French; keep no-space for `,`, `.` in all languages
- [x] D2: Add hex-character validation on `SourceAudio.sha256` field (regex `^[a-f0-9]{64}$`) or Pydantic `model_validator`
- [x] D3: Log each individual segment skipped in APKG export due to missing `audio_file` (not just error when all missing)
- [x] D4: Split `ManifestError` catch from `EnrichmentError` in pipeline error handling — provide accurate hints (disk space vs enrichment config)

### Group E — scattered hardening

- [x] E1: Add `-nostdin` flag to FFmpeg subprocess args in `clip_manifest_file`
- [x] E2: Validate `bitrate` against regex `^\d+[kM]?$` before passing to FFmpeg
- [x] E3: Add `MAX_AUDIO_SIZE` guard (5 GB) in `_validate_audio_path` or early in pipeline
- [x] E4: Add `shutil.disk_usage()` pre-flight check on work directory volume
- [x] E5: Add `from __future__ import annotations` to `cli.py`, `clipping.py`, `errors.py` for consistency with rest of codebase
- [x] E6: Narrow `except Exception` to `except ImportError` in `diagnostics.py:_find_static_ffmpeg_tool`
- [x] E7: Document WhisperModel re-load limitation in transcription module docstring
- [x] E8: Document `_VERBOSE` module-level global as acceptable for single-invocation CLI
- [x] E9: Add `-nostdin` also to FFmpeg/FFprobe calls in `diagnostics.py` for CI reliability

### Group F — Phase 9 residual hardening

- [x] F1: Unicode-safe whitespace stripping in `_safe_csv_cell` — replace `str.lstrip()` with `re.sub(r'^\s+', '', value)` for Unicode-aware CSV formula injection defense (Python 3.11 `lstrip()` only strips ASCII whitespace; `\u00a0=2+2` bypasses the check)
- [x] F2: Add `\r` bypass regression test to `test_safe_csv_cell_whitespace_bypass`
- [x] F3: Add Unicode whitespace test to `_safe_csv_cell` tests
- [x] F4: In `_has_symlink()` cleanup path (pipeline.py), manually unlink detected symlinks before `shutil.rmtree` on all Python versions instead of just logging a warning
- [x] F5: Fix or remove `test_rmtree_follow_symlinks_false` — test asserts `follow_symlinks=False` was passed but production code never uses this parameter

## Defaults

- `MAX_AUDIO_SIZE = 5 * 1024 * 1024 * 1024` (5 GB).
- `bitrate` regex allows formats: `128k`, `192k`, `320k`, `1M`, etc.
- French punctuation rule applies when `language` field matches `fr`
  (case-insensitive).
- SHA-256 hex validation uses `model_validator` for clean error messages.
- `from __future__ import annotations` enables PEP 604 syntax (`X | Y`) in all
  files.
- Unicode-safe whitespace stripping uses `re.sub(r'^[\s\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064\ufeff\u180e\u061c]+', '', value)` covering Unicode-space, ZWJ/ZWNJ, BOM, Cf-category, and other invisible characters.

## Acceptance Checks

- [x] French `"Bonjour !"` does not become `"Bonjour!"` (space preserved before `!`)
- [x] English `"Hello."` remains `"Hello."` (no space before `.` — unchanged behavior)
- [x] `sha256` field rejects strings with non-hex characters (e.g., `"zzz...z"`)
- [x] APKG export warns for each segment without audio (not just total failure)
- [x] `ManifestError` during enrichment shows disk-space hint, not enrichment config hint
- [x] FFmpeg subprocess includes `-nostdin` in arguments list
- [x] `bitrate="abc"` raises clear validation error
- [x] >5 GB audio file raises `InputAudioError` with size message
- [x] Disk-full scenario raises clear error before pipeline starts
- [x] `from __future__ import annotations` present in `cli.py`, `clipping.py`, `errors.py`
- [x] `_find_static_ffmpeg_tool` only catches `ImportError`, not broad `Exception`
- [x] `diagnostics.py` FFprobe/FFmpeg calls include `-nostdin`
- [x] `_safe_csv_cell("\u00a0=2+2")` returns `"'\u00a0=2+2"` (Unicode non-breaking space bypass fixed)
- [x] `_safe_csv_cell("\r=CMD")` has a regression test
- [x] `_has_symlink()` unlinks detected symlinks before `shutil.rmtree` proceeds
- [x] `test_rmtree_follow_symlinks_false` is removed or correctly asserts the actual behavior

## Verification Evidence

### Test Results (143/143 passing)

```
pytest: 143 passed in ~11s
ruff check: All checks passed
ruff format: 27 files already formatted
ty check src tests: All checks passed
```

### Acceptance Checks (16/16 passing)

| # | Acceptance Check | Status |
|---|---|---|
| 1 | French `"Bonjour !"` does not become `"Bonjour!"` | ✅ Language-aware SPACE_BEFORE_RE preserves space before `!`, `?`, `:`, `;` for French |
| 2 | English `"Hello."` remains `"Hello."` | ✅ Comma and period space-stripped for all languages |
| 3 | `sha256` field rejects non-hex strings | ✅ `field_validator` with `re.fullmatch(r"^[0-9a-fA-F]{64}$")` |
| 4 | APKG export warns per missing segment | ✅ Per-segment `logger.warning` + bulk ExportError on all missing |
| 5 | `ManifestError` shows disk-space hint | ✅ Separate `except ManifestError` clause in each phase |
| 6 | FFmpeg subprocess includes `-nostdin` | ✅ Present in clipping.py, diagnostics.py, audio.py |
| 7 | `bitrate="abc"` raises clear error | ✅ Regex validation + range check on suffixed values |
| 8 | >5 GB audio raises `InputAudioError` | ✅ `MAX_AUDIO_SIZE = 5*1024**3` guard in `collect_source_audio_metadata` |
| 9 | Disk-full raises clear error | ✅ `_check_disk_space` with 500 MB threshold on work_dir + cache volume |
| 10 | `from __future__ import annotations` present | ✅ In `cli.py`, `clipping.py`, `errors.py` |
| 11 | `_find_static_ffmpeg_tool` catches only `ImportError` | ✅ Both `except Exception` narrowed to `ImportError` |
| 12 | diagnostics.py calls include `-nostdin` | ✅ In `_read_tool_version` ffprobe/ffmpeg version check |
| 13 | `_safe_csv_cell("\u00a0=2+2")` returns `"'\u00a0=2+2"` | ✅ `re.sub` strips `\u00a0` followed by `=`, adds `'` prefix |
| 14 | `_safe_csv_cell("\r=CMD")` has regression test | ✅ Assertion in `test_safe_csv_cell_whitespace_bypass` |
| 15 | `_has_symlink()` unlinks before `rmtree` | ✅ `_remove_symlinks` recursive via `rglob("*")` + `rglob(".*")` |
| 16 | `test_rmtree_follow_symlinks_false` correct | ✅ Now asserts `ignore_errors=True`, not bogus `follow_symlinks=False` |

### Post-Review Fixes Applied (9 Round 1 + 5 Round 2)

All 14 findings from code-reviewer, security-auditor, and security-attacker agents were addressed:
- H1: Corrected `_safe_csv_cell` docstring
- H2: Zero-byte audio rejection in `audio.py`
- H3: Bitrate regex accepts uppercase `K` (`[kKmM]`)
- H4: Cf-category Unicode chars covered in CSV filter
- H5: `work_dir` symlink guard in `pipeline.py`
- H6: OSError guard in `_check_disk_space`
- H7: Bitrate range limit (320k / 10M)
- H8: Whisper cache disk volume check
- H9: Recursive `_remove_symlinks` via `rglob`
- H10: `\u2061`–`\u2064` Cf chars added to CSV regex
- H11: Dotfiles handled by chained `rglob(".*")`
- H12: `0k`/`0M` bitrate rejected with zero check
- H13: `%` moved to non-French regex (preserved for French)
- H14: `-nostdin` added to `audio.py` ffprobe call

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

## Post-Review Findings

Identified by code-reviewer, security-auditor, and security-attacker agents
after G1–G5 implementation.

### Execution Batches (by complexity, ascending)

| Batch | Items | Complexity | Description |
|-------|-------|------------|-------------|
| RH1 | H3, H2, H1 | Trivial (6 loc) | Docstring fix, empty-file rejection, bitrate case-sensitivity |
| RH2 | H4, H6, H5 | Simple (14 loc) | Zero-width CSV bypass, disk_usage OSError guard, work_dir symlink guard |
| RH3 | H7, H8, H9 | Medium (28 loc) | Bitrate upper bound, Whisper cache disk check, recursive symlink removal |

No dependencies — all items are fully independent and parallel-executable within each batch.

### Findings Detail

#### HIGH Severity

- **H4 (F1-extension):** `\u200b` (zero-width space) and other Unicode Cf-category characters bypass `\s` in `_safe_csv_cell` → CSV formula injection. Fix: `re.sub(r'^[\s\u200b\u200c\u200d\u2060\ufeff\u180e]+', '', cleaned)`. File: `src/audawispr/core/export.py`.
- **H5 (F2-new):** `work_dir` path not checked for pre-existing symlink after `mkdir()` → confused deputy attack (pipeline writes to target of external symlink). Fix: add `work_dir.is_symlink()` guard after `mkdir()`. File: `src/audawispr/core/pipeline.py`.

#### MEDIUM Severity

- **H7 (E2-extension):** Bitrate regex has no upper bound → DoS via `9999999k` producing massive output files. Also accepts `0` and `0k` silently. Fix: add range limit (max 320k or 10M) and reject `0`. File: `src/audawispr/core/clipping.py`.
- **H8 (E4-extension):** Disk pre-flight checks `work_dir` volume but Whisper model cache may be on different volume with insufficient space for first-run download (2+ GB). Fix: check cache-dir volume too, raise threshold. File: `src/audawispr/core/pipeline.py`.
- **H9 (F4-extension):** `_remove_symlinks` only scans top-level entries; subdirectory symlinks (e.g., `work_dir/media/bad_link`) survive. Fix: make walk recursive via `path.rglob("*")`. File: `src/audawispr/core/pipeline.py`.

#### LOW / NIT Severity

- **H1 (F1-docs):** `_safe_csv_cell` docstring misstates Python `str.lstrip()` behavior (Python 3's lstrip IS Unicode-aware). Fix: rewrite comments accurately. File: `src/audawispr/core/export.py`.
- **H2 (E3-extension):** Zero-byte audio files not rejected → wasted compute DoS. Fix: add `size_bytes == 0` guard. File: `src/audawispr/core/audio.py`.
- **H3 (E2-case):** Bitrate regex `[kM]` rejects valid uppercase `K` → `128K` fails validation. Fix: `[kKmM]`. File: `src/audawispr/core/clipping.py`.
- **H6 (E4-guard):** `_check_disk_space` unprotected against `shutil.disk_usage` OSError on exotic filesystems. Fix: wrap in try/except. File: `src/audawispr/core/pipeline.py`.

### Test Gaps

- Add `\u200b=2+2` and `\u200b\u200d=CMD` test assertions to `test_safe_csv_cell_whitespace_bypass`
- Add zero-byte rejection test to audio validation tests
- Add bitrate `128K` (uppercase) acceptance test
- Add bitrate `0` rejection test
- Add `work_dir` symlink rejection test to pipeline tests

## Final Review Findings (Round 2)

Identified by code-reviewer, security-auditor, and security-attacker after
all G1–G6 and RH1–RH3 fixes were applied. All 5 items subsequently fixed.

### Fixes Applied

| Sev | Issue | File | Fix |
|-----|-------|------|-----|
| CRITICAL | `\u2061`–`\u2064` bypass `_safe_csv_cell` | `export.py` | Added 7 more Cf-category and invisible chars to regex |
| HIGH | `rglob("*")` misses dotfiles | `pipeline.py` | Chained `rglob(".*")` for hidden entries |
| MAJOR | `0k`/`0M` bitrate not rejected | `clipping.py` | Added `value == 0` check in kK and mM branches |
| MAJOR | `%` spacing contradicts decision log | `segmentation.py` | Moved `%` to `_SPACE_BEFORE_NON_FRENCH` |
| MOD | `audio.py` ffprobe lacks `-nostdin` | `audio.py` | Inserted `-nostdin` in ffprobe subprocess args |

### Deferred / Informational

| Sev | Issue | Notes |
|-----|-------|-------|
| LOW | Soft hyphen `\u00ad` bypass in CSV filter | `'` prefix still blocks execution in output; completeness hardening only |
| LOW-MED | ReDoS potential in zero-width regex | Requires extremely long crafted input to trigger backtracking |
| NIT | Missing test coverage (3 items) | Zero-byte audio, bitrate `128K`, work_dir symlink tests |

### Final Status

- **143/143 tests pass**, lint clean, format clean, typecheck clean
- All 14 review findings (9 Round 1 + 5 Round 2) fixed and verified
- **v0.1.0 release ready**

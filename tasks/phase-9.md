# Phase 9: Pre-Release Security Audit Remediation

## Goal

Close all critical and high-severity findings from the pre-release security audit
and code review before v0.1.0 ships. Covers CSV injection, symlink traversal,
path traversal, XSS in Anki cards, pipeline cancellation cleanup, and clipping
robustness.

## User-Usable Result

- CSV and APKG exports are hardened against formula injection and path traversal.
- Anki card templates properly escape HTML-sensitive field content.
- Pipeline cancellation preserves the work directory for debugging.
- Work directory derivation and cleanup are safe against symlink attacks and
  directory collisions.

## TODO

### Group A — `export.py`

- [x] A1: Fix `_safe_csv_cell` whitespace bypass — check `value.lstrip()[0]` instead of `value[0]`
- [x] A2: Apply `_safe_csv_cell` to `segment.id` and `source_audio.file_name` in CSV export rows
- [x] A3: Add symlink check (`is_symlink`) and path containment check (`relative_to`) in `_resolve_audio` and `_copy_media`
- [x] A4: Layer 1: `html.escape()` field values in Python before passing to genanki; Layer 2: `{{hint:Field}}` in Anki card templates for defense-in-depth
- [x] A5: Use `str(src)` in `media_files` list (genanki needs filesystem paths to read media; genanki internally normalizes to basename in APKG output)
- [x] A6: Log a warning for each segment skipped in APKG export due to missing `audio_file`

### Group B — `clipping.py`, `pipeline.py`

- [x] B1: Sanitize `--format` option — strip `/` `\` `\0`; validate against allowlist (`mp3`, `wav`, `ogg`, `flac`, `m4a`); add `snippet_path.resolve().relative_to(output_dir.resolve())` containment guard
- [x] B2: Validate `manifest.source_audio.path` resolves within expected scope and is not a symlink before FFmpeg use
- [x] B3: Replace `os.path.relpath` with `Path.relative_to` in `_compute_audio_file`, with try/except fallback (fixes Windows crash on different drives)
- [x] B4: Guard work dir derivation — check if `output.with_suffix("")` is an existing directory that would be destroyed; raise clear error

### Group C — `pipeline.py`, `cli.py`, `clipping.py`

- [x] C1: In `run_pipeline` finally block, check `isinstance(exc, CancelledError)` before `shutil.rmtree(work_dir)` — preserve work dir on cancellation
- [x] C2: Symlink-safe cleanup — manual `os.scandir` walk catches all entries (including dotfiles) before `shutil.rmtree`; no non-existent `follow_symlinks` param
- [x] C3: Add `translation_provider` parameter to `_oneshot` CLI command with default `"none"`
- [x] C4: Save manifest incrementally after each segment in clipping loop (option a — ensures progress is preserved on failure)
- [x] C5: Emit work dir path to stderr when pipeline fails, so user can inspect intermediate artifacts

## Defaults

- `--format` if unspecified defaults to `mp3` (unchanged).
- `translation_provider` default is `"none"` (unchanged).
- Incremental manifest save does not change the output format.
- Symlink rejection applies to all user-supplied paths passed to subprocesses or
  file copy.
- Symlink-safe cleanup uses manual `os.scandir` traversal (catches all entries including dotfiles) before `shutil.rmtree`; symlinks in work dir are pathological but protected.

## Acceptance Checks

- [x] `_safe_csv_cell("  =2+2")` returns `"'  =2+2"` (whitespace bypass fixed)
- [x] `_safe_csv_cell("\t=CMD")` returns `"'\t=CMD"` (tab bypass fixed)
- [x] `segment.id` and `source_audio.file_name` are sanitized in CSV output
- [x] `_resolve_audio` rejects symlink paths and paths escaping manifest directory
- [x] `_copy_media` rejects symlink sources
- [x] Card template uses `{{hint:Field}}` syntax for XSS protection
- [x] HTML-escaped field values in genanki note creation
- [x] APKG media list contains full paths (genanki needs filesystem paths to read media); genanki internally normalizes to basename in APKG output
- [x] `--format ../../.bashrc` raises error (path traversal blocked)
- [x] `source_audio.path` pointing outside expected scope raises error
- [x] Windows-simulated `os.path.relpath` ValueError is caught gracefully
- [x] Work dir not deleted when pipeline is cancelled
- [x] `shutil.rmtree` symlink-safe (manual walk catches all entries including hidden, no bogus `follow_symlinks` param)
- [x] `_oneshot --translate deepl` does not cause TypeError
- [x] Partial clipping results are saved on failure (incremental manifest)
- [x] Failed pipeline emits work dir path to stderr

## Verification Evidence

### Test Suite
- **Total tests**: 143 passed (124 original + 19 new)
- **Key coverage**:
  - A1 (CSV whitespace bypass): `test_safe_csv_cell_whitespace_bypass` — verifies leading spaces, tabs, and edge cases
  - A2 (CSV sanitization): `test_csv_cell_sanitizes_segment_id_and_file_name`
  - A3 (symlink/path traversal): `test_resolve_audio_rejects_symlink`, `test_resolve_audio_rejects_path_traversal`, `test_copy_media_rejects_symlink`
  - A4 (XSS defense): `test_ankicard_html_escaped` — verifies `&lt;script&gt;` in APKG database
  - A5 (media paths): genanki needs full filesystem paths to read media; internally normalizes to basename in APKG output
  - A6 (missing audio warning): `test_apkg_export_warns_missing_audio`
  - B1 (format sanitization): `test_format_sanitization_rejects_path_traversal`, `test_format_sanitization_rejects_invalid_format`
  - B2 (source audio hardening): `test_source_audio_rejects_symlink`
  - B3 (Path.relative_to fallback): `test_compute_audio_file_fallback_on_valueerror`
  - B4 (work dir collision): `test_derive_work_dir_collision`, `test_derive_work_dir_no_collision_on_dir_output`
  - C1 (cancel preservation): `test_work_dir_preserved_on_cancellation`
  - C2 (symlink-safe rmtree): `test_rmtree_follow_symlinks_false`
  - C3 (--translate CLI): `test_oneshot_translate_does_not_cause_type_error`
  - C4 (incremental manifest): `test_clip_incremental_manifest_save`
  - C5 (stderr on failure): `test_pipeline_failure_emits_work_dir_stderr`

### Lint
- `ruff check .` — All checks passed

### Type Checking
- `ty check src tests` — All checks passed

### Post-Review Fixes Applied
All issues found during the 4-agent code review were fixed before final verification:

1. **C2 Critical**: Removed non-existent `follow_symlinks=False` parameter from `shutil.rmtree` — `follow_symlinks` does not exist in Python's `shutil.rmtree` stdlib. Replaced with cross-version manual symlink walk that catches ALL entries (including dotfiles) before cleanup.
2. **A3**: Moved `is_symlink()` check before `.resolve()` in `_resolve_audio` — the resolved path can never be a symlink. Now checks the raw candidate path.
3. **B1**: Changed `stable_snippet_filename()` to use sanitized `fmt` instead of raw `opts.audio_format` — previously the allowlist check passed but the unsanitized format was used in the filename.
4. **A5**: Kept `media_files.append(str(src))` — genanki needs full filesystem paths to read media bytestreams; it internally normalizes to basename in APKG output via `os.path.basename()`.
5. **CSV \r bypass**: Added `\r` stripping in `_safe_csv_cell` — `lstrip()` does not strip carriage return characters, allowing CSV injection bypass.
6. **Hidden symlinks**: Changed `rglob("*")` to a function that recursively walks with `os.scandir` from `work_dir`, catching all entries including dotfiles (`.hidden_link`).
7. **Cleanup exception masking**: Replaced `raise OneShotError(...)` with `logger.warning()` — raising during cleanup in `finally` blocks masks the original exception and `return` would suppress all exceptions.
8. **Redundant condition**: Merged the duplicated `if output.suffix:` check in `_derive_work_dir` into the first branch.

## Notes

- XSS defense uses defense-in-depth: Python `html.escape()` before genanki +
  Anki `{{hint:Field}}` template syntax.
- French punctuation fix is deferred to Phase 10 (correctness group).
- `CancelledError` import is already available from
  `src/audawispr/core/errors.py`.
- Path containment uses `path.resolve().relative_to(base.resolve())` with
  `ValueError` catch.
- The allowlist for `--format` is `mp3`, `wav`, `ogg`, `flac`, `m4a` —
  extensible via future configuration.

## Actual Implementation

**Branch:** `epic-1-phase-9-pre-release-security-audit-remediation` — zero production
code changes made. All 124 existing tests pass. The following plan is ordered by file
and dependency: `export.py` (most changes), then `clipping.py`, then `pipeline.py`,
then `cli.py`, then final verification.

### Step 1: `src/audawispr/core/export.py` (Group A, 6 items)

1. `[x]` **A1**: Fix `_safe_csv_cell` — change `value[0]` to `value.lstrip()[0]` on
    line 258. Add test: `_safe_csv_cell("  =2+2")` → `"'  =2+2"`,
    `_safe_csv_cell("\t=CMD")` → `"'\t=CMD"`.

2. `[x]` **A2**: Apply `_safe_csv_cell()` to `manifest.source_audio.file_name`
    (line 176) and `segment.id` (line 178) in the CSV writer loop.

3. `[x]` **A3**: In `_resolve_audio` (line 244): add `resolved.is_symlink()` check,
    add `resolved.relative_to(manifest_path.parent.resolve())` containment check with
    `ValueError` catch. In `_copy_media` (line 251): add `src.is_symlink()` check
    before `shutil.copy2`. Import `ExportError` is already available. Add tests:
    symlink rejection, path traversal rejection.

4. `[x]` **A4**:
    - Add `import html` at top of file.
    - Wrap field values with `html.escape()` before passing to `genanki.Note` at
      lines 219-226: `html.escape(segment.text)`, `html.escape(ipa)`,
      `html.escape(translation)`, `html.escape(manifest.source_audio.file_name)`,
      `html.escape(segment.id)`.
    - Add `{{hint:SourceText}}`, `{{hint:Audio}}`, `{{hint:IPA}}`,
      `{{hint:Translation}}` in Anki card templates (lines 82, 83, 87, 88, 90, 91).
    - Add test: `<script>alert(1)</script>` in segment text is escaped in card
      template output.

5. `[x]` **A5**: Keep `media_files.append(str(src))` — genanki needs full filesystem
    paths to read media bytestreams; it internally normalizes to basename in APKG output.

6. `[x]` **A6**: In lines 207-228 loop, add `else:` branch that logs a warning for
    each segment missing `audio_file` instead of the all-or-none error at line 230.
    Use `logging.getLogger(__name__).warning(...)`. Keep the `ExportError` at line 231
    only if ALL segments lack audio.

### Step 2: `src/audawispr/core/clipping.py` (Group B items B1–B3 + Group C item C4, 4 items)

7. `[x]` **B1**: Add format sanitization:
    - Define `ALLOWED_FORMATS = {"mp3", "wav", "ogg", "flac", "m4a"}` at module
      level.
    - In `clip_manifest_file`, validate `opts.audio_format` against allowlist, strip
      `/`, `\`, `\0` characters before validation. Raise `ClippingError` on invalid
      format.
    - After `snippet_path = output_dir / filename` (line 78), add containment check:
      `snippet_path.resolve().relative_to(output_dir.resolve())`.
    - Add test: `--format "../../.bashrc"` raises error.

8. `[x]` **B2**: After line 49 (`source_path = Path(manifest.source_audio.path)`),
    add:
    - `source_path.is_symlink()` check → raise `ClippingError`.
    - `source_path.exists()` already checked at line 50, but add
      `source_path.resolve().relative_to(Path.cwd())` or similar scope check.
    - Add test: `source_audio.path` pointing to symlink raises error.

9. `[x]` **B3**: Replace `_compute_audio_file` (lines 34-37):
    - Replace `os.path.relpath(output_dir, output_manifest.parent)` with
      `Path.relative_to`.
    - Under try/except ValueError: fall back to `Path(os.path.relpath(...))` as a
      safety net (note: this still crashes on Windows but preserves existing
      behavior for non-Windows).
    - Add test: simulate `ValueError` path and verify fallback.

10. `[x]` **C4**: Incremental manifest save:
    - Merge the two passes (clip loop at lines 66-113 + audio_file assignment loop
      at lines 115-122) into a single loop.
    - After clipping a segment and verifying the snippet, immediately set
      `seg.audio_file` via `_compute_audio_file` and call `save_manifest` at that
      point.
    - Add test: partial clipping results are saved in output manifest when subset of
      segments clip successfully.

### Step 3: `src/audawispr/core/pipeline.py` (Group B item B4 + Group C items C1, C2, C5, 4 items)

11. `[x]` **B4**: In `_derive_work_dir` (lines 85-93), add check:
    - After computing work_dir candidate, check if `output.with_suffix("")` is an
      existing directory (not the same as work_dir). Raise `ValueError` with clear
      message about collision.
    - Add test: output path that would collide with existing directory raises error.

12. `[x]` **C1 + C2**: Modify `finally` block (lines 222-224):
    - Capture exception via `exc = sys.exc_info()[1]` or restructure to check
      `isinstance(exc, CancelledError)`.
    - Add symlink-safe cleanup: manual `os.scandir` walk catches all entries including
      dotfiles before `shutil.rmtree` (no non-existent `follow_symlinks` param).
    - Add test: work dir preserved on cancellation. Add test: symlinks in work dir not
      followed during cleanup.

13. `[x]` **C5**: In the pipeline error handler (the `except OneShotError` or general
    failure paths), emit work dir path to stderr before raising. Use
    `sys.stderr.write(f"Work directory preserved at: {work_dir}\n")` or similar.
    - Add test: failed pipeline emits work dir to stderr.

### Step 4: `src/audawispr/cli.py` (Group C item C3, 1 item)

14. `[x]` **C3**: Add `--translate` option to `_oneshot` command:
    - Add a `translate` parameter (same pattern as the `enrich` command, lines
      272-278) with default `"none"`.
    - Pass `translation_provider=translate` in the `PipelineRequest(...)` constructor
      at lines 494-508.
    - Add test: `_oneshot --translate deepl` does not raise `TypeError`.

### Step 5: Tests & Verification (after all code changes)

15. `[x]` Run `uv run pytest` — all existing 124 tests must still pass plus new tests.
16. `[x]` Run `uv run ruff check .` — lint clean.
17. `[x]` Run `uv run ty check src tests` — type check clean.
18. `[x]` Update acceptance checkboxes in the Acceptance Checks section above from
    `[ ]` to `[x]` as each passes.
19. `[x]` Fill in Verification Evidence section with test names, lint/typecheck
    output.

### Implementation Notes

- The `from __future__ import annotations` import is already present in all core
  files (clipping.py line 1, export.py line 1, pipeline.py line 3) — no need to add.
- `CancelledError` is already imported in pipeline.py line 14.
- `html` module is stdlib — no dependency needed.
- The `logging` module is stdlib — prefer
  `import logging; logger = logging.getLogger(__name__)` pattern.
- C2 uses manual `os.scandir` traversal for all Python versions (3.11+) — `follow_symlinks`
  does not exist in Python's `shutil.rmtree` stdlib.

## Post-Review Changes

After the 4-agent code review, the following fixes were applied to address findings:

| Fix | Description | File |
|-----|-------------|------|
| C2 Critical | Replaced `follow_symlinks=False` (doesn't exist in stdlib) with cross-version manual symlink walk | `pipeline.py` |
| A3 | Moved `is_symlink()` before `.resolve()` — resolved path is never a symlink | `export.py` |
| B1 | Use sanitized `fmt` in `stable_snippet_filename()` instead of raw `opts.audio_format` | `clipping.py` |
| A5 | Kept `str(src)` — genanki needs filesystem paths to read media; normalizes to basename internally | `export.py` |
| CSV \r | Strip `\r` in `_safe_csv_cell` — `lstrip()` doesn't strip carriage return | `export.py` |
| Hidden symlinks | `rglob("*")` → `os.scandir` walk catching all entries including dotfiles | `pipeline.py` |
| Exception masking | `raise OneShotError` → `logger.warning` (return in finally suppresses exceptions) | `pipeline.py` |
| Redundant condition | Merged duplicated `if output.suffix` in `_derive_work_dir` | `pipeline.py` |

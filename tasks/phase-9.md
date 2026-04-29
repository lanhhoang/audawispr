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

- [ ] A1: Fix `_safe_csv_cell` whitespace bypass — check `value.lstrip()[0]` instead of `value[0]`
- [ ] A2: Apply `_safe_csv_cell` to `segment.id` and `source_audio.file_name` in CSV export rows
- [ ] A3: Add symlink check (`is_symlink`) and path containment check (`relative_to`) in `_resolve_audio` and `_copy_media`
- [ ] A4: Layer 1: `html.escape()` field values in Python before passing to genanki; Layer 2: `{{hint:Field}}` in Anki card templates for defense-in-depth
- [ ] A5: Use `src.name` (basename only) in `media_files` list, not `str(src)` full path
- [ ] A6: Log a warning for each segment skipped in APKG export due to missing `audio_file`

### Group B — `clipping.py`, `pipeline.py`

- [ ] B1: Sanitize `--format` option — strip `/` `\` `\0`; validate against allowlist (`mp3`, `wav`, `ogg`, `flac`, `m4a`); add `snippet_path.resolve().relative_to(output_dir.resolve())` containment guard
- [ ] B2: Validate `manifest.source_audio.path` resolves within expected scope and is not a symlink before FFmpeg use
- [ ] B3: Replace `os.path.relpath` with `Path.relative_to` in `_compute_audio_file`, with try/except fallback (fixes Windows crash on different drives)
- [ ] B4: Guard work dir derivation — check if `output.with_suffix("")` is an existing directory that would be destroyed; raise clear error

### Group C — `pipeline.py`, `cli.py`, `clipping.py`

- [ ] C1: In `run_pipeline` finally block, check `isinstance(exc, CancelledError)` before `shutil.rmtree(work_dir)` — preserve work dir on cancellation
- [ ] C2: Add `follow_symlinks=False` to `shutil.rmtree(work_dir, ...)` call
- [ ] C3: Add `translation_provider` parameter to `_oneshot` CLI command with default `"none"`
- [ ] C4: Save manifest incrementally after each segment in clipping loop (option a — ensures progress is preserved on failure)
- [ ] C5: Emit work dir path to stderr when pipeline fails, so user can inspect intermediate artifacts

## Defaults

- `--format` if unspecified defaults to `mp3` (unchanged).
- `translation_provider` default is `"none"` (unchanged).
- Incremental manifest save does not change the output format.
- Symlink rejection applies to all user-supplied paths passed to subprocesses or
  file copy.
- `follow_symlinks=False` is defense-in-depth; symlinks in work dir are
  pathological but protected.

## Acceptance Checks

- [ ] `_safe_csv_cell("  =2+2")` returns `"'  =2+2"` (whitespace bypass fixed)
- [ ] `_safe_csv_cell("\t=CMD")` returns `"'\t=CMD"` (tab bypass fixed)
- [ ] `segment.id` and `source_audio.file_name` are sanitized in CSV output
- [ ] `_resolve_audio` rejects symlink paths and paths escaping manifest directory
- [ ] `_copy_media` rejects symlink sources
- [ ] Card template uses `{{hint:Field}}` syntax for XSS protection
- [ ] HTML-escaped field values in genanki note creation
- [ ] APKG media list contains only basenames, not absolute paths
- [ ] `--format ../../.bashrc` raises error (path traversal blocked)
- [ ] `source_audio.path` pointing outside expected scope raises error
- [ ] Windows-simulated `os.path.relpath` ValueError is caught gracefully
- [ ] Work dir not deleted when pipeline is cancelled
- [ ] `shutil.rmtree` called with `follow_symlinks=False`
- [ ] `_oneshot --translate deepl` does not cause TypeError
- [ ] Partial clipping results are saved on failure (incremental manifest)
- [ ] Failed pipeline emits work dir path to stderr

## Verification Evidence

(to be filled after implementation)

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

1. `[ ]` **A1**: Fix `_safe_csv_cell` — change `value[0]` to `value.lstrip()[0]` on
    line 258. Add test: `_safe_csv_cell("  =2+2")` → `"'  =2+2"`,
    `_safe_csv_cell("\t=CMD")` → `"'\t=CMD"`.

2. `[ ]` **A2**: Apply `_safe_csv_cell()` to `manifest.source_audio.file_name`
    (line 176) and `segment.id` (line 178) in the CSV writer loop.

3. `[ ]` **A3**: In `_resolve_audio` (line 244): add `resolved.is_symlink()` check,
    add `resolved.relative_to(manifest_path.parent.resolve())` containment check with
    `ValueError` catch. In `_copy_media` (line 251): add `src.is_symlink()` check
    before `shutil.copy2`. Import `ExportError` is already available. Add tests:
    symlink rejection, path traversal rejection.

4. `[ ]` **A4**:
    - Add `import html` at top of file.
    - Wrap field values with `html.escape()` before passing to `genanki.Note` at
      lines 219-226: `html.escape(segment.text)`, `html.escape(ipa)`,
      `html.escape(translation)`, `html.escape(manifest.source_audio.file_name)`,
      `html.escape(segment.id)`.
    - Add `{{hint:SourceText}}`, `{{hint:Audio}}`, `{{hint:IPA}}`,
      `{{hint:Translation}}` in Anki card templates (lines 82, 83, 87, 88, 90, 91).
    - Add test: `<script>alert(1)</script>` in segment text is escaped in card
      template output.

5. `[ ]` **A5**: Change line 210 from `media_files.append(str(src))` to
    `media_files.append(src.name)`.

6. `[ ]` **A6**: In lines 207-228 loop, add `else:` branch that logs a warning for
    each segment missing `audio_file` instead of the all-or-none error at line 230.
    Use `logging.getLogger(__name__).warning(...)`. Keep the `ExportError` at line 231
    only if ALL segments lack audio.

### Step 2: `src/audawispr/core/clipping.py` (Group B items B1–B3 + Group C item C4, 4 items)

7. `[ ]` **B1**: Add format sanitization:
    - Define `ALLOWED_FORMATS = {"mp3", "wav", "ogg", "flac", "m4a"}` at module
      level.
    - In `clip_manifest_file`, validate `opts.audio_format` against allowlist, strip
      `/`, `\`, `\0` characters before validation. Raise `ClippingError` on invalid
      format.
    - After `snippet_path = output_dir / filename` (line 78), add containment check:
      `snippet_path.resolve().relative_to(output_dir.resolve())`.
    - Add test: `--format "../../.bashrc"` raises error.

8. `[ ]` **B2**: After line 49 (`source_path = Path(manifest.source_audio.path)`),
    add:
    - `source_path.is_symlink()` check → raise `ClippingError`.
    - `source_path.exists()` already checked at line 50, but add
      `source_path.resolve().relative_to(Path.cwd())` or similar scope check.
    - Add test: `source_audio.path` pointing to symlink raises error.

9. `[ ]` **B3**: Replace `_compute_audio_file` (lines 34-37):
    - Replace `os.path.relpath(output_dir, output_manifest.parent)` with
      `Path.relative_to`.
    - Under try/except ValueError: fall back to `Path(os.path.relpath(...))` as a
      safety net (note: this still crashes on Windows but preserves existing
      behavior for non-Windows).
    - Add test: simulate `ValueError` path and verify fallback.

10. `[ ]` **C4**: Incremental manifest save:
    - Merge the two passes (clip loop at lines 66-113 + audio_file assignment loop
      at lines 115-122) into a single loop.
    - After clipping a segment and verifying the snippet, immediately set
      `seg.audio_file` via `_compute_audio_file` and call `save_manifest` at that
      point.
    - Add test: partial clipping results are saved in output manifest when subset of
      segments clip successfully.

### Step 3: `src/audawispr/core/pipeline.py` (Group B item B4 + Group C items C1, C2, C5, 4 items)

11. `[ ]` **B4**: In `_derive_work_dir` (lines 85-93), add check:
    - After computing work_dir candidate, check if `output.with_suffix("")` is an
      existing directory (not the same as work_dir). Raise `ValueError` with clear
      message about collision.
    - Add test: output path that would collide with existing directory raises error.

12. `[ ]` **C1 + C2**: Modify `finally` block (lines 222-224):
    - Capture exception via `exc = sys.exc_info()[1]` or restructure to check
      `isinstance(exc, CancelledError)`.
    - Add `follow_symlinks=False` to the `shutil.rmtree` call.
    - Add test: work dir preserved on cancellation. Add test: symlinks in work dir not
      followed during cleanup.

13. `[ ]` **C5**: In the pipeline error handler (the `except OneShotError` or general
    failure paths), emit work dir path to stderr before raising. Use
    `sys.stderr.write(f"Work directory preserved at: {work_dir}\n")` or similar.
    - Add test: failed pipeline emits work dir to stderr.

### Step 4: `src/audawispr/cli.py` (Group C item C3, 1 item)

14. `[ ]` **C3**: Add `--translate` option to `_oneshot` command:
    - Add a `translate` parameter (same pattern as the `enrich` command, lines
      272-278) with default `"none"`.
    - Pass `translation_provider=translate` in the `PipelineRequest(...)` constructor
      at lines 494-508.
    - Add test: `_oneshot --translate deepl` does not raise `TypeError`.

### Step 5: Tests & Verification (after all code changes)

15. `[ ]` Run `uv run pytest` — all existing 124 tests must still pass plus new tests.
16. `[ ]` Run `uv run ruff check .` — lint clean.
17. `[ ]` Run `uv run ty check src tests` — type check clean.
18. `[ ]` Update acceptance checkboxes in the Acceptance Checks section above from
    `[ ]` to `[x]` as each passes.
19. `[ ]` Fill in Verification Evidence section with test names, lint/typecheck
    output.

### Implementation Notes

- The `from __future__ import annotations` import is already present in all core
  files (clipping.py line 1, export.py line 1, pipeline.py line 3) — no need to add.
- `CancelledError` is already imported in pipeline.py line 14.
- `html` module is stdlib — no dependency needed.
- The `logging` module is stdlib — prefer
  `import logging; logger = logging.getLogger(__name__)` pattern.
- For C2, `follow_symlinks=False` was added in Python 3.12's `shutil.rmtree` — the
  project targets Python 3.11+, so check if this parameter is available. If not, use
  `os.path.islink` checks manually.

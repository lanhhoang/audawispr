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

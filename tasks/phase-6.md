# Phase 6: Importable Anki CSV Export

## Goal

Add a useful pre-APKG export target that creates Anki-compatible rows and media
files. After this phase, users can manually import cards into Anki without
waiting for native `.apkg` support.

## User-Usable Result

- `uv run audawispr export out/clipped.json --format anki-csv --output out/anki-csv`
  writes `out/anki-csv/cards.csv` and `out/anki-csv/media/`.

## TODO

- [ ] Add export options and result types for file-backed and in-memory
  manifest export.
- [ ] Implement media resolution and deterministic media copying for segment
  snippets.
- [ ] Implement `anki-csv` writer at `cards.csv` with stable field order.
- [ ] Write CSV with UTF-8 encoding and Python `csv` newline handling to avoid
  platform-specific line ending bugs.
- [ ] Include source text, audio reference, IPA, translation, source filename,
  timestamp range, and segment ID fields.
- [ ] Write audio references in Anki sound syntax, such as
  `[sound:0001_seg-0001.mp3]`.
- [ ] Document manual import expectations in README, including how copied media
  should be made available to Anki.
- [ ] Add `audawispr export` CLI with `--format anki-csv` and output path.
- [ ] Add clear errors for missing audio files, unsupported formats, and invalid
  manifests.
- [ ] Preserve manifest-driven reruns without retranscription, segmentation, or
  clipping.

## Defaults

- CSV field order:
  `SourceText`, `Audio`, `IPA`, `Translation`, `SourceFile`,
  `TimestampRange`, `SegmentId`.
- Copied media goes under `<output>/media/`.
- Audio references in CSV use media basenames only, not OS-specific paths.
- CSV export is manual-import assisted, not a fully self-contained import. The
  README must explain that media may need to be copied into Anki's collection
  media folder depending on the user's import flow.

## Acceptance Checks

- [ ] Tests for field order and row values.
- [ ] Tests for media copying and audio references.
- [ ] Tests for `[sound:...]` syntax.
- [ ] Tests for UTF-8 text and newline-safe CSV output.
- [ ] Tests for missing snippet errors.
- [ ] Tests for deterministic reruns.
- [ ] README documents CSV import and media handling.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr export --help`
- [ ] CI quality workflow passes.

## Notes

- Do not implement native `.apkg` export in this phase.
- The CSV should be usable for manual Anki import with media copied alongside
  it.

## Verification Evidence

- Pending.

---

## Actual Implementation

### Prerequisite Check

The following are already implemented and do NOT need to be redone:

- `src/audawispr/core/manifest.py`: `TranscriptSegment` already has `audio_file`, `ipa`, `translation`, `text`, `id`, `start`, `end` fields.
- `src/audawispr/core/errors.py`: Already has `AudawisprError` base class.
- CLI pattern, atomic writes, `ty` config, and CI workflow are already in place.
- `src/audawispr/core/clipping.py`: `clip_manifest_file` produces manifests with `audio_file` paths that Phase 6 will use.

### Implementation Steps

#### 1. `src/audawispr/core/errors.py`

Add `ExportError` after `ClippingError`:

```python
class ExportError(AudawisprError):
    """Raised when manifest export cannot produce valid output."""
```

#### 2. `src/audawispr/core/export.py` (new file)

Implement:

- **`ExportOptions`** dataclass (frozen):
  - `format: str = "anki-csv"`
  - Future phases will add `apkg` etc.

- **`export_manifest_file(manifest_path: Path, output_dir: Path, options: ExportOptions) -> None`**:
  1. Load manifest from `manifest_path`.
  2. If `options.format != "anki-csv"`, raise `ExportError`.
  3. Create `output_dir / "media"` directory.
  4. For each segment:
     - Resolve `audio_file` path: `manifest_path.parent / segment.audio_file`.
     - Copy file to `output_dir / "media" / <basename>` using `shutil.copy2`.
     - If source file missing, raise `ExportError`.
  5. Write `output_dir / "cards.csv"` with `csv.writer`:
     - `lineterminator="\n"`, `utf-8` encoding.
     - Header: `SourceText`, `Audio`, `IPA`, `Translation`, `SourceFile`, `TimestampRange`, `SegmentId`.
     - One row per segment:
       - `SourceText`: segment.text
       - `Audio`: `[sound:<snippet_basename>]`
       - `IPA`: segment.ipa or `""`
       - `Translation`: segment.translation or `""`
       - `SourceFile`: manifest.source_audio.file_name
       - `TimestampRange`: `f"{segment.start:.3f}-{segment.end:.3f}"`
       - `SegmentId`: segment.id
  6. Use atomic temp-write + replace for CSV file.

- **`_resolve_audio(manifest_path: Path, audio_file: str) -> Path`**:
  - Resolve `audio_file` relative to `manifest_path.parent`.
  - Check file exists, raise `ExportError` if missing.
  - Return resolved path.

- **`_copy_media(src: Path, dest_dir: Path) -> None`**:
  - Copy with `shutil.copy2` for metadata preservation.
  - Create `dest_dir` if it doesn't exist.

#### 3. `src/audawispr/core/__init__.py`

Add exports:
```python
from audawispr.core.export import ExportOptions, export_manifest_file
```

Add to `__all__`:
```python
    "ExportOptions",
    "export_manifest_file",
```

#### 4. `src/audawispr/cli.py`

Add `export` command with `--format` and `--output` options:

```python
@app.command()
def export(
    manifest: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Clipped manifest JSON to export.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for CSV and media.",
        ),
    ],
    format: Annotated[
        str,
        typer.Option("--format", help="Export format. Epic 1 supports only 'anki-csv'."),
    ] = "anki-csv",
) -> None:
    """Export a clipped manifest to Anki-compatible format."""
```

- Add imports: `from audawispr.core.export import ExportOptions, export_manifest_file`
- Add `ExportError` to existing error imports.
- Error handling via `_fail()`.

#### 5. `tests/test_export.py` (new file)

- `test_export_field_order` — CSV header and row field order
- `test_export_audio_sound_syntax` — Audio column uses `[sound:...]`
- `test_export_ipa_null_becomes_empty` — null IPA → empty cell
- `test_export_translation_field` — translation preserved
- `test_export_source_file` — SourceFile column
- `test_export_timestamp_range` — format `start-end`
- `test_export_segment_id` — SegmentId column
- `test_export_media_copying` — files copied to `<output>/media/`
- `test_export_missing_snippet_error` — missing audio file raises error
- `test_export_utf8_encoding` — UTF-8 text preserved
- `test_export_unsupported_format` — bad format raises error
- `test_export_deterministic_rerun` — second call produces identical output

#### 6. `tests/test_cli.py`

Add:
- `test_export_help_displays_phase_6_options` — `--format`, `--output`
- `test_export_writes_csv` — mock `export_manifest_file`, check stdout
- `test_export_reports_error` — mock `export_manifest_file` raises `ExportError`, check stderr
- Add `"export"` to `test_help_displays_cli_name` assertions

#### 7. `tests/test_core_exports.py`

Add:
```python
from audawispr.core import ExportOptions, export_manifest_file
```
```python
    assert ExportOptions().format == "anki-csv"
    assert callable(export_manifest_file)
```

#### 8. `README.md`

Add section after `clip`:

```markdown
Export a clipped manifest for Anki import:

```sh
uv run audawispr export out/clipped.json --format anki-csv --output out/anki-csv
```

`export` reads a clipped manifest, copies audio snippets, and writes
`out/anki-csv/cards.csv` with columns `SourceText`, `Audio`, `IPA`,
`Translation`, `SourceFile`, `TimestampRange`, and `SegmentId`. Audio
references use Anki's `[sound:...]` syntax.

Manual import in Anki Desktop: File → Import → select `cards.csv`,
set "Fields separated by: Comma", and copy the `media/` folder contents
into your Anki collection.media folder.
```

#### 9. `tasks/epic-1.md` update

- After local coding + testing passes + CI passes: update Phase 6 row to `✅ Done`
- Pending CI during local work: `⏳ Pending, need CI status confirmation`

### Notes for Implementation

- Use `csv.writer` with `lineterminator="\n"` to avoid platform-specific line endings.
- Use `^` as the `csv.writer` escape char if needed (Anki expects standard CSV).
- Media basenames: `Path(segment.audio_file).name` gives the filename from the POSIX-style path.
- `shutil.copy2` preserves file metadata.
- Atomic write for CSV: same `NamedTemporaryFile` + `os.replace` pattern used in `manifest.py`.
- `source_audio.file_name` is available from the manifest (e.g. `lesson.mp3`).
- Timestamp range format: `{start:.3f}-{end:.3f}`.
- Unset fields (`ipa`, `translation` = `None`) become empty strings in CSV.

### Completion Criteria

Phase 6 is only considered fully complete when the remote GitHub Actions CI workflow passes. Do not mark Phase 6 as "Done" in `tasks/epic-1.md` after local implementation — the epic tracker will be updated manually after CI validation.

import json
import logging
import sqlite3
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from audawispr.core.errors import ExportError
from audawispr.core.export import (
    ExportOptions,
    _copy_media,
    _resolve_audio,
    _safe_csv_cell,
    export_manifest_file,
)
from audawispr.core.manifest import (
    SourceAudio,
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
)


def _make_clipped_manifest(
    tmp_path: Path,
    audio_files: list[str] | None = None,
) -> TranscriptManifest:
    if audio_files is None:
        audio_files = ["media/0000_seg-0000.mp3", "media/0001_seg-0001.mp3"]
    return TranscriptManifest(
        language="fr",
        source_audio=SourceAudio(
            file_name="lesson.mp3",
            path=str(tmp_path / "lesson.mp3"),
            size_bytes=3,
            sha256="0" * 64,
            language="fr",
            duration_seconds=5.0,
        ),
        transcription=TranscriptionSettings(
            model_size="small",
            device="auto",
            compute_type="int8",
            vad=True,
        ),
        segments=[
            TranscriptSegment(
                id="seg-0000",
                start=0.0,
                end=1.5,
                text="Bonjour le monde.",
                words=[
                    TranscriptWord(text="Bonjour", start=0.0, end=0.5),
                    TranscriptWord(text="le", start=0.6, end=0.8),
                    TranscriptWord(text="monde.", start=0.9, end=1.5),
                ],
                ipa="bɔ̃ʒuʀ lə mɔ̃d.",
                translation=None,
                audio_file=audio_files[0],
            ),
            TranscriptSegment(
                id="seg-0001",
                start=2.0,
                end=3.0,
                text="Comment ça va?",
                words=[
                    TranscriptWord(text="Comment", start=2.0, end=2.3),
                    TranscriptWord(text="ça", start=2.4, end=2.6),
                    TranscriptWord(text="va?", start=2.7, end=3.0),
                ],
                ipa=None,
                translation="How's it going?",
                audio_file=audio_files[1],
            ),
        ],
    )


def _write_manifest(tmp_path: Path, manifest: TranscriptManifest) -> Path:
    path = tmp_path / "clipped.json"
    path.write_text(manifest.model_dump_json(), encoding="utf-8")
    return path


def _make_snippets(tmp_path: Path, manifest: TranscriptManifest) -> None:
    manifest_dir = tmp_path
    for seg in manifest.segments:
        if seg.audio_file:
            snippet = manifest_dir / seg.audio_file
            snippet.parent.mkdir(parents=True, exist_ok=True)
            snippet.write_bytes(b"fake audio data")


# --- Field order and row values ---


def test_export_field_order(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)

    csv_path = output_dir / "cards.csv"
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    header = lines[0].split(",")
    assert header == [
        "Sentence",
        "Audio",
        "IPA",
        "Translation",
        "SourceFile",
        "TimestampRange",
        "SegmentId",
    ]


def test_export_audio_sound_syntax(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)
    csv_path = output_dir / "cards.csv"
    lines = csv_path.read_text(encoding="utf-8").splitlines()

    # Row 1: seg-0000
    row1 = lines[1].split(",")
    assert row1[1] == "[sound:0000_seg-0000.mp3]"

    # Row 2: seg-0001
    row2 = lines[2].split(",")
    assert row2[1] == "[sound:0001_seg-0001.mp3]"


def test_export_ipa_null_becomes_empty(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)
    csv_path = output_dir / "cards.csv"
    lines = csv_path.read_text(encoding="utf-8").splitlines()

    row1 = lines[1].split(",")
    assert row1[2] == "bɔ̃ʒuʀ lə mɔ̃d."

    row2 = lines[2].split(",")
    assert row2[2] == ""  # ipa is None


def test_export_translation_field(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)
    csv_path = output_dir / "cards.csv"
    lines = csv_path.read_text(encoding="utf-8").splitlines()

    row1 = lines[1].split(",")
    assert row1[3] == ""  # translation is None

    row2 = lines[2].split(",")
    assert "How" in row2[3]


def test_export_source_file(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)
    csv_path = output_dir / "cards.csv"
    lines = csv_path.read_text(encoding="utf-8").splitlines()

    row1 = lines[1].split(",")
    assert row1[4] == "lesson.mp3"


def test_export_timestamp_range(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)
    csv_path = output_dir / "cards.csv"
    lines = csv_path.read_text(encoding="utf-8").splitlines()

    row1 = lines[1].split(",")
    assert row1[5] == "0.000-1.500"

    row2 = lines[2].split(",")
    assert row2[5] == "2.000-3.000"


def test_export_segment_id(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)
    csv_path = output_dir / "cards.csv"
    lines = csv_path.read_text(encoding="utf-8").splitlines()

    assert lines[1].split(",")[6] == "seg-0000"
    assert lines[2].split(",")[6] == "seg-0001"


# --- Media copying ---


def test_export_media_copying(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)

    media_dir = output_dir / "media"
    assert media_dir.exists()
    assert (media_dir / "0000_seg-0000.mp3").exists()
    assert (media_dir / "0001_seg-0001.mp3").exists()


def test_export_missing_snippet_error(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    with pytest.raises(ExportError, match="no segments with audio files to export"):
        export_manifest_file(manifest_path, output_dir)


# --- UTF-8 ---


def test_export_utf8_encoding(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    manifest.segments[0].text = "Ça va très bien été."
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)
    csv_path = output_dir / "cards.csv"
    content = csv_path.read_text(encoding="utf-8")
    assert "Ça va très bien été." in content


# --- Unsupported format ---


def test_export_unsupported_format(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    with pytest.raises(ExportError, match="unsupported export format"):
        export_manifest_file(manifest_path, output_dir, ExportOptions(format="pdf"))


# --- Deterministic rerun ---


def test_export_deterministic_rerun(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)
    first_csv = (output_dir / "cards.csv").read_bytes()

    export_manifest_file(manifest_path, output_dir)
    second_csv = (output_dir / "cards.csv").read_bytes()

    assert first_csv == second_csv


# --- APKG export ---


def test_export_apkg_file_created(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    export_manifest_file(manifest_path, apkg_path)

    assert apkg_path.exists()
    assert apkg_path.stat().st_size > 0


def test_export_apkg_media_included(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    export_manifest_file(manifest_path, apkg_path)

    with zipfile.ZipFile(apkg_path, "r") as zf:
        names = zf.namelist()
        assert "media" in names, f"ZIP entries: {names}"


def test_export_apkg_deck_name(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "custom.apkg"

    export_manifest_file(
        manifest_path,
        apkg_path,
        ExportOptions(format="apkg", deck_name="My French Deck"),
    )

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with zipfile.ZipFile(apkg_path, "r") as zf:
        zf.extract("collection.anki2", extract_dir)

    conn = sqlite3.connect(extract_dir / "collection.anki2")
    decks_json = conn.execute("SELECT decks FROM col").fetchone()[0]
    conn.close()

    assert "My French Deck" in decks_json


def test_export_apkg_default_deck_name(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    export_manifest_file(manifest_path, apkg_path)

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with zipfile.ZipFile(apkg_path, "r") as zf:
        zf.extract("collection.anki2", extract_dir)

    conn = sqlite3.connect(extract_dir / "collection.anki2")
    decks_json = conn.execute("SELECT decks FROM col").fetchone()[0]
    conn.close()

    assert "audawispr::fr" in decks_json


def test_export_apkg_card_template(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    export_manifest_file(manifest_path, apkg_path)

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with zipfile.ZipFile(apkg_path, "r") as zf:
        zf.extract("collection.anki2", extract_dir)

    conn = sqlite3.connect(extract_dir / "collection.anki2")
    models_json = conn.execute("SELECT models FROM col").fetchone()[0]
    conn.close()

    assert '"css": ' in models_json
    assert "source-text" in models_json
    assert "metadata" in models_json
    assert "&middot;" in models_json


def test_export_apkg_generates_cards_for_each_note(tmp_path: Path) -> None:
    """Regression: every note must generate exactly one card (single-template model).

    The genanki library's _req computation fails on {{hint:FieldName}} Mustache
    syntax, causing zero cards when any optional field (IPA, Translation) is empty.
    """
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    export_manifest_file(manifest_path, apkg_path)

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with zipfile.ZipFile(apkg_path, "r") as zf:
        zf.extract("collection.anki2", extract_dir)

    conn = sqlite3.connect(extract_dir / "collection.anki2")
    note_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    card_count = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    conn.close()

    assert note_count == 2
    # Single-template model: every note should generate exactly 1 card
    assert card_count == note_count


def test_export_apkg_stable_guid(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    export_manifest_file(manifest_path, apkg_path)
    with zipfile.ZipFile(apkg_path, "r") as zf:
        zf.extract("collection.anki2", tmp_path)
    conn = sqlite3.connect(tmp_path / "collection.anki2")
    first_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    first_guids = [row[0] for row in conn.execute("SELECT guid FROM notes").fetchall()]
    conn.close()

    (tmp_path / "collection.anki2").unlink()

    export_manifest_file(manifest_path, apkg_path)
    with zipfile.ZipFile(apkg_path, "r") as zf:
        zf.extract("collection.anki2", tmp_path)
    conn = sqlite3.connect(tmp_path / "collection.anki2")
    second_count = conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
    second_guids = [row[0] for row in conn.execute("SELECT guid FROM notes").fetchall()]
    conn.close()

    assert first_count == second_count == 2
    assert first_guids == second_guids


def test_export_apkg_missing_snippet_error(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    with pytest.raises(ExportError, match="no segments with audio files to export"):
        export_manifest_file(manifest_path, apkg_path)


def test_export_apkg_empty_manifest_error(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    for seg in manifest.segments:
        seg.audio_file = None
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    with pytest.raises(ExportError, match="no segments with audio files to export"):
        export_manifest_file(manifest_path, apkg_path)


def test_export_infer_apkg_from_path(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    # No explicit format — suffix .apkg should infer apkg
    export_manifest_file(manifest_path, apkg_path)

    assert apkg_path.exists()
    assert apkg_path.stat().st_size > 0


def test_export_csv_still_works(tmp_path: Path) -> None:
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)

    assert (output_dir / "cards.csv").exists()
    assert (output_dir / "media" / "0000_seg-0000.mp3").exists()


# --- Security: CSV formula injection (A1, A2) ---


def test_safe_csv_cell_whitespace_bypass() -> None:
    """Leading whitespace should not bypass formula-injection protection."""
    assert _safe_csv_cell("  =2+2") == "'  =2+2"
    assert _safe_csv_cell("\t=CMD") == "'\t=CMD"
    # Whitespace-only strings should be returned unchanged
    assert _safe_csv_cell("   ") == "   "
    assert _safe_csv_cell("") == ""
    # \r bypass regression: carriage return stripped before lstrip
    assert _safe_csv_cell("\r=CMD") == "'=CMD"
    # Unicode whitespace bypass (F1): \u00a0 (non-breaking space) stripped
    assert _safe_csv_cell("\u00a0=2+2") == "'\u00a0=2+2"
    # Zero-width Unicode characters must not bypass (Cf category)
    assert _safe_csv_cell("\u200b=2+2") == "'\u200b=2+2"
    assert _safe_csv_cell("\u200b\u200d=CMD") == "'\u200b\u200d=CMD"


def test_csv_cell_sanitizes_segment_id_and_file_name(tmp_path: Path) -> None:
    """CSV output should sanitize manifest.source_audio.file_name and segment.id."""
    manifest = _make_clipped_manifest(tmp_path)
    manifest.segments[0].id = "=HYPERLINK(...)"
    manifest.source_audio.file_name = "+EVIL()"
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    output_dir = tmp_path / "anki-csv"

    export_manifest_file(manifest_path, output_dir)

    csv_path = output_dir / "cards.csv"
    content = csv_path.read_text(encoding="utf-8")

    # SourceFile column should be sanitized
    assert "'+EVIL()" in content
    # SegmentId column should be sanitized
    assert "'=HYPERLINK(" in content


# --- Security: symlink and path-traversal rejection (A3) ---


def test_resolve_audio_rejects_symlink(tmp_path: Path) -> None:
    """_resolve_audio must reject paths that appear to be symlinks."""
    manifest_path = tmp_path / "manifest.json"
    audio_file = tmp_path / "audio.mp3"
    audio_file.write_bytes(b"data")

    with patch.object(Path, "is_symlink", return_value=True):
        with pytest.raises(ExportError, match="audio file is a symlink"):
            _resolve_audio(manifest_path, "audio.mp3")


def test_resolve_audio_rejects_path_traversal(tmp_path: Path) -> None:
    """_resolve_audio must reject paths that escape the manifest directory."""
    outside = tmp_path / "outside.mp3"
    outside.write_bytes(b"data")

    manifest_dir = tmp_path / "manifest_dir"
    manifest_dir.mkdir()
    manifest_path = manifest_dir / "manifest.json"

    with pytest.raises(ExportError, match="audio file escapes manifest directory"):
        _resolve_audio(manifest_path, "../outside.mp3")


def test_copy_media_rejects_symlink(tmp_path: Path) -> None:
    """_copy_media must reject symlink sources."""
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"data")

    with patch.object(Path, "is_symlink", return_value=True):
        with pytest.raises(ExportError, match="audio file is a symlink"):
            _copy_media(src, tmp_path)


# --- Security: XSS defense in APKG (A4) ---


def test_ankicard_html_escaped(tmp_path: Path) -> None:
    """APKG note fields should have HTML-special characters escaped."""
    manifest = _make_clipped_manifest(tmp_path)
    manifest.segments[0].text = "<script>alert('xss')</script>"
    manifest.segments[0].ipa = "<b>ipa</b>"
    manifest.segments[0].translation = "a & b"
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    export_manifest_file(manifest_path, apkg_path)

    extract_dir = tmp_path / "extract"
    extract_dir.mkdir()
    with zipfile.ZipFile(apkg_path, "r") as zf:
        zf.extract("collection.anki2", extract_dir)

    conn = sqlite3.connect(extract_dir / "collection.anki2")
    notes = conn.execute("SELECT flds FROM notes").fetchall()
    conn.close()

    for (flds,) in notes:
        if "&lt;script&gt;" in flds:
            assert "&lt;b&gt;ipa&lt;/b&gt;" in flds
            assert "a &amp; b" in flds
            break
    else:
        pytest.fail("No note with HTML-escaped content found")


# --- Security: media files are basenames in APKG (A5) ---


def test_media_files_basename_only(tmp_path: Path) -> None:
    """APKG media JSON should contain only basenames, never full paths."""
    manifest = _make_clipped_manifest(tmp_path)
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    export_manifest_file(manifest_path, apkg_path)

    with zipfile.ZipFile(apkg_path, "r") as zf:
        media_json = json.loads(zf.read("media").decode("utf-8"))

    for idx, filename in media_json.items():
        assert "/" not in filename, (
            f"media file {idx} contains path separator: {filename!r}"
        )


# --- Per-segment warning for missing audio (A6) ---


def test_apkg_export_warns_missing_audio(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """APKG export should warn about segments that have no audio_file."""
    manifest = _make_clipped_manifest(tmp_path)
    manifest.segments[1].audio_file = None
    _make_snippets(tmp_path, manifest)
    manifest_path = _write_manifest(tmp_path, manifest)
    apkg_path = tmp_path / "deck.apkg"

    with caplog.at_level(logging.WARNING):
        export_manifest_file(manifest_path, apkg_path)

    assert apkg_path.exists()
    assert "has no audio file" in caplog.text
    assert "seg-0001" in caplog.text

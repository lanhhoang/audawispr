from __future__ import annotations

import csv
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import genanki

from audawispr.core.errors import ExportError
from audawispr.core.manifest import TranscriptManifest, load_manifest

DECK_ID = 2059400110
MODEL_ID = 2059400111
MODEL_NAME = "audawispr Segment Card"

ANKI_MODEL = genanki.Model(
    MODEL_ID,
    MODEL_NAME,
    fields=[
        {"name": "SourceText"},
        {"name": "Audio"},
        {"name": "IPA"},
        {"name": "Translation"},
        {"name": "SourceFile"},
        {"name": "TimestampRange"},
        {"name": "SegmentId"},
    ],
    templates=[
        {
            "name": "Card 1",
            "qfmt": "{{SourceText}}<br>{{Audio}}",
            "afmt": (
                '{{FrontSide}}<hr id="answer">'
                "{{IPA}}<br>{{Translation}}<br>{{SourceFile}}<br>{{TimestampRange}}"
            ),
        },
    ],
)


@dataclass(frozen=True)
class ExportOptions:
    format: str = "anki-csv"
    deck_name: str | None = None


def export_manifest_file(
    manifest_path: Path,
    output_path: Path,
    options: ExportOptions | None = None,
) -> None:
    opts = options or ExportOptions()
    manifest = load_manifest(manifest_path)

    if opts.format == "apkg" or output_path.suffix == ".apkg":
        _export_apkg(manifest, manifest_path, output_path, opts)
        return

    if opts.format != "anki-csv":
        raise ExportError(f"unsupported export format: {opts.format}")

    _export_csv(manifest, manifest_path, output_path)


def _export_csv(
    manifest: TranscriptManifest,
    manifest_path: Path,
    output_dir: Path,
) -> None:
    resolved_output = output_dir.expanduser()
    media_dir = resolved_output / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    for segment in manifest.segments:
        if segment.audio_file:
            src = _resolve_audio(manifest_path, segment.audio_file)
            _copy_media(src, media_dir)

    csv_path = resolved_output / "cards.csv"
    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=resolved_output,
            prefix=f".{csv_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            writer = csv.writer(temp_file, lineterminator="\n")
            writer.writerow(
                [
                    "SourceText",
                    "Audio",
                    "IPA",
                    "Translation",
                    "SourceFile",
                    "TimestampRange",
                    "SegmentId",
                ]
            )
            for segment in manifest.segments:
                basename = Path(segment.audio_file).name if segment.audio_file else ""
                sound_ref = f"[sound:{basename}]" if basename else ""
                ipa = segment.ipa if segment.ipa is not None else ""
                translation = (
                    segment.translation if segment.translation is not None else ""
                )
                writer.writerow(
                    [
                        _safe_csv_cell(segment.text),
                        sound_ref,
                        _safe_csv_cell(ipa),
                        _safe_csv_cell(translation),
                        manifest.source_audio.file_name,
                        f"{segment.start:.3f}-{segment.end:.3f}",
                        segment.id,
                    ]
                )
        os.replace(temp_path, csv_path)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise ExportError(f"could not write CSV: {exc}") from exc


def _export_apkg(
    manifest: TranscriptManifest,
    manifest_path: Path,
    output_path: Path,
    opts: ExportOptions,
) -> None:
    deck_name = opts.deck_name or f"audawispr::{manifest.language}"
    deck = genanki.Deck(deck_id=DECK_ID, name=deck_name)

    sha256 = manifest.source_audio.sha256

    class AudawisprNote(genanki.Note):
        @property
        def guid(self) -> str:
            assert self.fields is not None
            return genanki.guid_for(sha256, self.fields[6])

    media_files: list[str] = []

    for segment in manifest.segments:
        if segment.audio_file:
            src = _resolve_audio(manifest_path, segment.audio_file)
            media_files.append(str(src))

            basename = src.name
            sound_ref = f"[sound:{basename}]"
            ipa = segment.ipa if segment.ipa is not None else ""
            translation = segment.translation if segment.translation is not None else ""
            note = AudawisprNote(
                model=ANKI_MODEL,
                fields=[
                    segment.text,
                    sound_ref,
                    ipa,
                    translation,
                    manifest.source_audio.file_name,
                    f"{segment.start:.3f}-{segment.end:.3f}",
                    segment.id,
                ],
            )
            deck.add_note(note)

    if len(deck.notes) == 0:
        raise ExportError("no segments with audio files to export")

    resolved_output = output_path.expanduser()
    resolved_output.parent.mkdir(parents=True, exist_ok=True)

    try:
        package = genanki.Package(deck)
        package.media_files = media_files
        package.write_to_file(str(resolved_output))
    except OSError as exc:
        raise ExportError(f"could not write APKG: {exc}") from exc


def _resolve_audio(manifest_path: Path, audio_file: str) -> Path:
    resolved = (manifest_path.parent / audio_file).resolve()
    if not resolved.exists():
        raise ExportError(f"audio file does not exist: {resolved}")
    return resolved


def _copy_media(src: Path, dest_dir: Path) -> None:
    dest = dest_dir / src.name
    shutil.copy2(src, dest)


def _safe_csv_cell(value: str) -> str:
    """Neutralize CSV formula injection in spreadsheet apps."""
    if value and value[0] in "=+-@":
        return "'" + value
    return value

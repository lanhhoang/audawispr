from __future__ import annotations

import csv
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from audawispr.core.errors import ExportError
from audawispr.core.manifest import load_manifest


@dataclass(frozen=True)
class ExportOptions:
    format: str = "anki-csv"


def export_manifest_file(
    manifest_path: Path,
    output_dir: Path,
    options: ExportOptions | None = None,
) -> None:
    opts = options or ExportOptions()

    if opts.format != "anki-csv":
        raise ExportError(f"unsupported export format: {opts.format}")

    manifest = load_manifest(manifest_path)

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
                        segment.text,
                        sound_ref,
                        ipa,
                        translation,
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


def _resolve_audio(manifest_path: Path, audio_file: str) -> Path:
    resolved = (manifest_path.parent / audio_file).resolve()
    if not resolved.exists():
        raise ExportError(f"audio file does not exist: {resolved}")
    return resolved


def _copy_media(src: Path, dest_dir: Path) -> None:
    dest = dest_dir / src.name
    shutil.copy2(src, dest)

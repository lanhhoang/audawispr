"""Timestamp-aware transcript segmentation."""

from __future__ import annotations

import csv
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from audawispr.core.errors import SegmentationError
from audawispr.core.manifest import (
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
)

TERMINAL_PUNCTUATION = (".", "!", "?", "...")
_SPACE_BEFORE_ALWAYS = re.compile(r"\s+([,.%])")
_SPACE_BEFORE_NON_FRENCH = re.compile(r"\s+([:;!?])")
SPACE_AFTER_OPEN_RE = re.compile(r"([(\[{])\s+")
TSV_TEXT_WHITESPACE_RE = re.compile(r"[\t\r\n]+")
TIMING_EPSILON_SECONDS = 1e-9


@dataclass(frozen=True)
class SegmentationOptions:
    """User-selectable timestamp segmentation settings."""

    pause_split_ms: int = 700
    min_duration_ms: int = 600
    max_duration_ms: int = 7000
    merge_short: bool = True

    def __post_init__(self) -> None:
        if self.pause_split_ms < 0:
            raise SegmentationError("pause_split_ms must be greater than or equal to 0")
        if self.min_duration_ms <= 0:
            raise SegmentationError("min_duration_ms must be greater than 0")
        if self.max_duration_ms <= 0:
            raise SegmentationError("max_duration_ms must be greater than 0")
        if self.max_duration_ms < self.min_duration_ms:
            raise SegmentationError(
                "max_duration_ms must be greater than or equal to min_duration_ms"
            )

    @property
    def pause_split_seconds(self) -> float:
        return self.pause_split_ms / 1000

    @property
    def min_duration_seconds(self) -> float:
        return self.min_duration_ms / 1000

    @property
    def max_duration_seconds(self) -> float:
        return self.max_duration_ms / 1000


def segment_manifest(
    manifest: TranscriptManifest,
    options: SegmentationOptions | None = None,
) -> TranscriptManifest:
    """Rebuild transcript segments into sentence-like learning units."""
    segmentation_options = options or SegmentationOptions()
    words = _flatten_words(manifest)
    chunks = _split_words(words, segmentation_options)
    if segmentation_options.merge_short:
        chunks = _merge_short_chunks(
            chunks,
            segmentation_options.min_duration_seconds,
            segmentation_options.max_duration_seconds,
        )
    segments = [
        _build_segment(index, chunk, manifest.language)
        for index, chunk in enumerate(chunks)
    ]

    try:
        return TranscriptManifest(
            schema_version=manifest.schema_version,
            app_version=manifest.app_version,
            created_at=manifest.created_at,
            language=manifest.language,
            source_audio=manifest.source_audio,
            transcription=manifest.transcription,
            segments=segments,
        )
    except ValidationError as exc:
        raise SegmentationError(f"segmented manifest is invalid: {exc}") from exc


def default_inspection_tsv_path(output_manifest_path: Path) -> Path:
    """Return the default inspection TSV path for a segmented manifest output."""
    return output_manifest_path.expanduser().with_suffix(".tsv")


def save_inspection_tsv(manifest: TranscriptManifest, path: Path) -> None:
    """Atomically write a TSV for human inspection of segmented units."""
    destination = path.expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            writer = csv.writer(temp_file, delimiter="\t", lineterminator="\n")
            writer.writerow(["id", "index", "start", "end", "text"])
            for index, segment in enumerate(manifest.segments):
                writer.writerow(
                    [
                        segment.id,
                        index,
                        _format_seconds(segment.start),
                        _format_seconds(segment.end),
                        _format_tsv_text(segment.text),
                    ]
                )
        os.replace(temp_path, destination)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise SegmentationError(f"could not save inspection TSV: {exc}") from exc


def _flatten_words(manifest: TranscriptManifest) -> list[TranscriptWord]:
    words = [word for segment in manifest.segments for word in segment.words]
    if not words:
        raise SegmentationError("manifest has no word timestamps")

    previous_word: TranscriptWord | None = None
    for word in words:
        if not word.text.strip():
            raise SegmentationError("word timestamp has empty text")
        if not math.isfinite(word.start) or not math.isfinite(word.end):
            raise SegmentationError("word timestamps must be finite")
        if previous_word is not None and word.start < previous_word.end:
            raise SegmentationError(
                "word timestamps must be monotonic and non-overlapping"
            )
        previous_word = word
    return words


def _split_words(
    words: list[TranscriptWord],
    options: SegmentationOptions,
) -> list[list[TranscriptWord]]:
    chunks: list[list[TranscriptWord]] = []
    current: list[TranscriptWord] = []

    for word in words:
        if current:
            previous_word = current[-1]
            would_exceed_max = (
                word.end - current[0].start > options.max_duration_seconds
            )
            pause_exceeds_threshold = (
                word.start - previous_word.end >= options.pause_split_seconds
                and _meets_min_duration(
                    previous_word.end - current[0].start,
                    options.min_duration_seconds,
                )
            )
            if would_exceed_max or pause_exceeds_threshold:
                chunks.append(current)
                current = []

        current.append(word)
        if _ends_sentence(word.text) and _meets_min_duration(
            current[-1].end - current[0].start,
            options.min_duration_seconds,
        ):
            chunks.append(current)
            current = []

    if current:
        chunks.append(current)

    return chunks


def _merge_short_chunks(
    chunks: list[list[TranscriptWord]],
    min_duration_seconds: float,
    max_duration_seconds: float,
) -> list[list[TranscriptWord]]:
    merged: list[list[TranscriptWord]] = []
    index = 0

    while index < len(chunks):
        chunk = chunks[index]
        if (
            _meets_min_duration(_duration(chunk), min_duration_seconds)
            or len(chunks) == 1
        ):
            merged.append(chunk)
            index += 1
            continue

        if index + 1 < len(chunks) and _within_max_duration(
            _duration(chunk + chunks[index + 1]),
            max_duration_seconds,
        ):
            chunks[index + 1] = chunk + chunks[index + 1]
            index += 1
            continue

        if merged and _within_max_duration(
            _duration(merged[-1] + chunk),
            max_duration_seconds,
        ):
            merged[-1].extend(chunk)
        else:
            merged.append(chunk)
        index += 1

    return merged


def _build_segment(
    index: int, words: list[TranscriptWord], language: str | None = None
) -> TranscriptSegment:
    if not words:
        raise SegmentationError("cannot build an empty segment")
    return TranscriptSegment(
        id=f"seg-{index:04d}",
        start=words[0].start,
        end=words[-1].end,
        text=_join_words(words, language=language),
        words=words,
    )


def _join_words(words: list[TranscriptWord], language: str | None = None) -> str:
    text = " ".join(word.text.strip() for word in words)
    text = _SPACE_BEFORE_ALWAYS.sub(r"\1", text)
    if language is None or not language.lower().startswith("fr"):
        text = _SPACE_BEFORE_NON_FRENCH.sub(r"\1", text)
    return SPACE_AFTER_OPEN_RE.sub(r"\1", text)


def _duration(words: list[TranscriptWord]) -> float:
    return words[-1].end - words[0].start


def _ends_sentence(text: str) -> bool:
    stripped_text = text.strip()
    return stripped_text.endswith(TERMINAL_PUNCTUATION)


def _format_seconds(value: float) -> str:
    return f"{value:.3f}"


def _format_tsv_text(value: str) -> str:
    return TSV_TEXT_WHITESPACE_RE.sub(" ", value).strip()


def _meets_min_duration(duration: float, minimum: float) -> bool:
    return duration + TIMING_EPSILON_SECONDS >= minimum


def _within_max_duration(duration: float, maximum: float) -> bool:
    return duration <= maximum + TIMING_EPSILON_SECONDS

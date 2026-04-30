"""Local transcription pipeline backed by faster-whisper.

Note: ``WhisperModel`` is re-loaded on every ``transcribe()`` call.
This is acceptable for single-invocation CLI usage but should not be
used in tight loops.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, SupportsFloat, SupportsIndex

from pydantic import ValidationError

from audawispr.core.audio import collect_source_audio_metadata
from audawispr.core.errors import TranscriptionError
from audawispr.core.manifest import (
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
)


@dataclass(frozen=True)
class TranscriptionOptions:
    """User-selectable local transcription settings."""

    language: str = "fr"
    model_size: str = "small"
    device: str = "auto"
    compute_type: str = "int8"
    vad: bool = True


class TranscriptionBackend(Protocol):
    """Backend interface used by CLI tests and future engines."""

    def transcribe(
        self,
        audio_path: Path,
        options: TranscriptionOptions,
    ) -> list[TranscriptSegment]:
        """Return transcript segments for a source audio file."""


class FasterWhisperBackend:
    """Transcription backend using faster-whisper."""

    def transcribe(
        self,
        audio_path: Path,
        options: TranscriptionOptions,
    ) -> list[TranscriptSegment]:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - dependency is installed
            raise TranscriptionError("faster-whisper is not installed") from exc

        try:
            model = WhisperModel(
                options.model_size,
                device=options.device,
                compute_type=options.compute_type,
            )
        except Exception as exc:
            message = f"could not initialize Whisper model: {exc}"
            raise TranscriptionError(message) from exc

        try:
            raw_segments, _info = model.transcribe(
                str(audio_path),
                language=options.language,
                vad_filter=options.vad,
                word_timestamps=True,
            )
            return [
                _convert_segment(index, segment)
                for index, segment in enumerate(raw_segments)
            ]
        except TranscriptionError:
            raise
        except Exception as exc:
            raise TranscriptionError(f"transcription failed: {exc}") from exc


def transcribe_audio(
    audio_path: Path,
    options: TranscriptionOptions,
    *,
    backend: TranscriptionBackend | None = None,
) -> TranscriptManifest:
    """Transcribe source audio into a validated transcript manifest."""
    source_audio = collect_source_audio_metadata(audio_path, options.language)
    resolved_audio_path = Path(source_audio.path)
    transcription_backend = backend or FasterWhisperBackend()
    segments = transcription_backend.transcribe(resolved_audio_path, options)

    if not segments:
        raise TranscriptionError("transcription produced no segments")

    try:
        return TranscriptManifest(
            language=options.language,
            source_audio=source_audio,
            transcription=TranscriptionSettings(
                model_size=options.model_size,
                device=options.device,
                compute_type=options.compute_type,
                vad=options.vad,
                word_timestamps=True,
            ),
            segments=segments,
        )
    except ValidationError as exc:
        raise TranscriptionError(f"generated manifest is invalid: {exc}") from exc


def _convert_segment(index: int, segment: Any) -> TranscriptSegment:
    raw_words = segment.words
    if not raw_words:
        raise TranscriptionError("transcription segment is missing word timestamps")

    words = [
        TranscriptWord(
            text=str(word.word).strip(),
            start=float(word.start),
            end=float(word.end),
            probability=_optional_float(word.probability),
        )
        for word in raw_words
    ]
    if not words:
        raise TranscriptionError("transcription segment is missing word timestamps")

    segment_id = segment.id if segment.id is not None else index
    formatted_id = f"seg-{segment_id:04d}"
    return TranscriptSegment(
        id=formatted_id,
        start=float(segment.start),
        end=float(segment.end),
        text=str(segment.text).strip(),
        words=words,
    )


def _optional_float(
    value: str | bytes | SupportsFloat | SupportsIndex | None,
) -> float | None:
    if value is None:
        return None
    return float(value)

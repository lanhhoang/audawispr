"""Local transcription pipeline backed by faster-whisper.

Note: ``WhisperModel`` is re-loaded on every ``transcribe()`` call.
This is acceptable for single-invocation CLI usage but should not be
used in tight loops.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, SupportsFloat, SupportsIndex

from pydantic import ValidationError

from audawispr.core.audio import collect_source_audio_metadata
from audawispr.core.errors import DependencyError, TranscriptionError
from audawispr.core.manifest import (
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
)

_WHISPER_MODEL_SIZES: dict[str, str] = {
    "tiny.en": "Systran/faster-whisper-tiny.en",
    "tiny": "Systran/faster-whisper-tiny",
    "base.en": "Systran/faster-whisper-base.en",
    "base": "Systran/faster-whisper-base",
    "small.en": "Systran/faster-whisper-small.en",
    "small": "Systran/faster-whisper-small",
    "medium.en": "Systran/faster-whisper-medium.en",
    "medium": "Systran/faster-whisper-medium",
    "large-v1": "Systran/faster-whisper-large-v1",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    "large": "Systran/faster-whisper-large-v3",
    "distil-large-v2": "Systran/faster-distil-whisper-large-v2",
    "distil-medium.en": "Systran/faster-distil-whisper-medium.en",
    "distil-small.en": "Systran/faster-distil-whisper-small.en",
    "distil-large-v3": "Systran/faster-distil-whisper-large-v3",
    "distil-large-v3.5": "distil-whisper/distil-large-v3.5-ct2",
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
}


_WHISPER_ALLOW_PATTERNS: list[str] = [
    "config.json",
    "preprocessor_config.json",
    "model.bin",
    "tokenizer.json",
    "vocabulary.*",
]
# Matches faster-whisper's own download_model() allow_patterns exactly.
# Keep in sync with faster_whisper.utils._MODELS if upstream adds new file types.


WHISPER_VALID_SIZES: frozenset[str] = frozenset(_WHISPER_MODEL_SIZES)

_HF_CACHE_INDICATOR = os.path.join(".cache", "huggingface")


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


def install_whisper_model(
    model_size: str,
    *,
    cache_dir: str | None = None,
    force: bool = False,
) -> str:
    """Pre-download a Whisper model from HuggingFace Hub with progress bars.

    Uses ``huggingface_hub.snapshot_download()`` directly to get real download
    progress (faster-whisper's own ``download_model()`` suppresses progress via
    ``disabled_tqdm``).

    When ``force=False`` (default), returns the cached path immediately if the
    model is already in the local HuggingFace cache — no network access.
    When ``force=True``, any locally cached snapshot is deleted before
    downloading a fresh copy.

    Args:
        model_size: Model size alias (e.g. ``"small"``, ``"medium"``, ``"large-v3"``)
            or a HuggingFace repo ID (e.g. ``"Systran/faster-whisper-small"``).
        cache_dir: Override the default HuggingFace cache directory.
        force: Re-download even if the model is already cached.

    Returns:
        Absolute path to the cached model directory.

    Raises:
        DependencyError: On download failure (network, disk, auth).
        ValueError: If ``model_size`` is not a recognized alias and not a repo ID.
    """
    # Resolve size alias → HuggingFace repo ID
    if "/" in model_size:
        repo_id = model_size
    else:
        repo_id = _WHISPER_MODEL_SIZES.get(model_size)
        if repo_id is None:
            raise ValueError(
                f"Unknown model size: {model_size!r}. "
                f"Valid sizes: {', '.join(sorted(_WHISPER_MODEL_SIZES))}"
            )

    # Probe cache — skip download if already present (unless force)
    if not force:
        try:
            from faster_whisper.utils import download_model as fw_download

            return fw_download(model_size, local_files_only=True)
        except Exception:  # ImportError, LocalEntryNotFoundError, ValueError
            pass

    # Force: delete cached snapshot if it exists
    if force:
        try:
            from faster_whisper.utils import download_model as fw_download

            cached = fw_download(model_size, local_files_only=True)
            if cached and _HF_CACHE_INDICATOR in str(cached):
                shutil.rmtree(cached)
            elif cached:
                raise DependencyError(
                    f"Refusing to delete cache path outside HuggingFace cache: {cached}"
                )
        except DependencyError:  # re-raise the error above
            raise
        except Exception:  # not cached — nothing to delete
            pass

    # Download with progress bars
    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise DependencyError(
            "huggingface_hub is required for model download. "
            "`faster-whisper` should already have this installed."
        ) from exc

    try:
        return snapshot_download(
            repo_id,
            cache_dir=cache_dir,
            allow_patterns=_WHISPER_ALLOW_PATTERNS,
            # No tqdm_class override → uses huggingface_hub's default hf_tqdm
            # which shows real-time download progress bars.
        )
    except Exception as exc:
        raise DependencyError(
            f"Failed to download Whisper model {model_size!r}: {exc}"
        ) from exc

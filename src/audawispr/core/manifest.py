"""Versioned transcript manifest models and JSON helpers."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from audawispr.__about__ import __version__
from audawispr.core.errors import ManifestError

SCHEMA_VERSION = "1.0"


class SourceAudio(BaseModel):
    """Metadata for the local source audio used to create a transcript."""

    model_config = ConfigDict(extra="forbid")

    file_name: str
    path: str
    size_bytes: int = Field(ge=0)
    sha256: str = Field(min_length=64, max_length=64)

    @field_validator("sha256", mode="after")
    @classmethod
    def _check_sha256_hex(cls, value: str) -> str:
        if not re.fullmatch(r"^[0-9a-fA-F]{64}$", value):
            raise ValueError(
                f"sha256 must be a 64-character hex string, got: "
                f"{value[:20]}{'...' if len(value) > 20 else ''}"
            )
        return value

    language: str = Field(min_length=1)
    duration_seconds: float | None = Field(default=None, ge=0)


class TranscriptionSettings(BaseModel):
    """Settings used by the local transcription backend."""

    model_config = ConfigDict(extra="forbid")

    backend: Literal["faster-whisper"] = "faster-whisper"
    model_size: str = Field(min_length=1)
    device: str = Field(min_length=1)
    compute_type: str = Field(min_length=1)
    vad: bool
    word_timestamps: Literal[True] = True


class TranscriptWord(BaseModel):
    """One transcribed word with Whisper timestamps."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    probability: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_word_timing(self) -> TranscriptWord:
        if self.end < self.start:
            msg = "word end must be greater than or equal to start"
            raise ValueError(msg)
        return self


class TranscriptSegment(BaseModel):
    """One raw transcript segment produced by Whisper."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    text: str = Field(min_length=1)
    words: list[TranscriptWord] = Field(min_length=1)
    ipa: str | None = None
    translation: str | None = None
    translation_provider: str | None = None
    audio_file: str | None = None

    @model_validator(mode="after")
    def validate_segment_timing(self) -> TranscriptSegment:
        if self.end < self.start:
            msg = "segment end must be greater than or equal to start"
            raise ValueError(msg)

        previous_word: TranscriptWord | None = None
        for word in self.words:
            if word.start < self.start or word.end > self.end:
                msg = "word timestamps must fall within segment timestamps"
                raise ValueError(msg)
            if previous_word is not None and word.start < previous_word.start:
                msg = "word timestamps must be monotonic within a segment"
                raise ValueError(msg)
            previous_word = word
        return self


class TranscriptManifest(BaseModel):
    """A validated local transcript manifest."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = SCHEMA_VERSION
    app_version: str = __version__
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    language: str = Field(min_length=1)
    source_audio: SourceAudio
    transcription: TranscriptionSettings
    segments: list[TranscriptSegment] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_manifest_timing(self) -> TranscriptManifest:
        previous_segment: TranscriptSegment | None = None
        for segment in self.segments:
            if previous_segment is not None and segment.start < previous_segment.end:
                msg = "segment timestamps must be monotonic and non-overlapping"
                raise ValueError(msg)
            previous_segment = segment
        if self.source_audio.language != self.language:
            msg = "manifest language must match source audio language"
            raise ValueError(msg)
        return self


def save_manifest(manifest: TranscriptManifest, path: Path) -> None:
    """Atomically write a transcript manifest as formatted JSON."""
    destination = path.expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = manifest.model_dump(mode="json")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)
            json.dump(payload, temp_file, ensure_ascii=False, indent=2)
            temp_file.write("\n")
        os.replace(temp_path, destination)
    except OSError as exc:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise ManifestError(f"could not save manifest: {exc}") from exc


def load_manifest(path: Path) -> TranscriptManifest:
    """Load and validate a transcript manifest from JSON."""
    try:
        with path.expanduser().open(encoding="utf-8") as manifest_file:
            payload: Any = json.load(manifest_file)
    except FileNotFoundError as exc:
        raise ManifestError(f"manifest does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ManifestError(f"manifest is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise ManifestError(f"could not read manifest: {exc}") from exc

    try:
        return TranscriptManifest.model_validate(payload)
    except ValidationError as exc:
        raise ManifestError(str(exc)) from exc

"""Source audio metadata helpers."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from audawispr.core.diagnostics import FFPROBE_ENV, find_media_tool
from audawispr.core.errors import InputAudioError
from audawispr.core.manifest import SourceAudio

MAX_AUDIO_SIZE = 5 * 1024 * 1024 * 1024


def collect_source_audio_metadata(path: Path, language: str) -> SourceAudio:
    """Collect stable metadata for a source audio file."""
    resolved_path = _validate_audio_path(path)

    size_bytes = resolved_path.stat().st_size
    if size_bytes >= MAX_AUDIO_SIZE:
        raise InputAudioError(
            f"Audio file too large: {size_bytes / (1024**3):.1f} GiB "
            f"(max {MAX_AUDIO_SIZE / (1024**3):.0f} GiB)"
        )

    if size_bytes == 0:
        raise InputAudioError("audio file is empty")

    return SourceAudio(
        file_name=resolved_path.name,
        path=str(resolved_path),
        size_bytes=size_bytes,
        sha256=_sha256_file(resolved_path),
        language=language,
        duration_seconds=_read_duration_seconds(resolved_path),
    )


def _validate_audio_path(path: Path) -> Path:
    try:
        resolved_path = path.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise InputAudioError(f"input audio does not exist: {path}") from exc
    except OSError as exc:
        raise InputAudioError(f"could not resolve input audio: {exc}") from exc

    if resolved_path.is_dir():
        raise InputAudioError(f"input audio is a directory: {path}")
    if not resolved_path.is_file():
        raise InputAudioError(f"input audio is not a file: {path}")

    try:
        with resolved_path.open("rb"):
            pass
    except OSError as exc:
        raise InputAudioError(f"input audio is not readable: {exc}") from exc

    return resolved_path


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as audio_file:
            for chunk in iter(lambda: audio_file.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise InputAudioError(f"could not hash input audio: {exc}") from exc
    return digest.hexdigest()


def _read_duration_seconds(path: Path) -> float | None:
    ffprobe = find_media_tool("ffprobe", FFPROBE_ENV)
    if not ffprobe.available or ffprobe.path is None:
        return None

    try:
        completed = subprocess.run(
            [
                ffprobe.path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None

    try:
        duration = float(completed.stdout.strip())
    except ValueError:
        return None
    return duration if duration >= 0 else None

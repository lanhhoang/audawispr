from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from audawispr.core.diagnostics import FFMPEG_ENV, find_media_tool
from audawispr.core.errors import ClippingError
from audawispr.core.manifest import TranscriptManifest, load_manifest, save_manifest

ALLOWED_FORMATS = {"mp3", "wav", "ogg", "flac", "m4a"}


@dataclass(frozen=True)
class ClipOptions:
    padding_before_ms: int = 150
    padding_after_ms: int = 250
    audio_format: str = "mp3"
    bitrate: str = "128k"
    force: bool = False


def safe_segment_id(segment_id: str) -> str:
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")
    result = "".join(ch if ch in allowed else "-" for ch in segment_id)
    result = result.strip(".-")
    result = result[:80]
    return result if result else "segment"


def stable_snippet_filename(index: int, segment_id: str, extension: str) -> str:
    return f"{index:04d}_{safe_segment_id(segment_id)}.{extension}"


def _compute_audio_file(output_manifest: Path, output_dir: Path, filename: str) -> str:
    try:
        rel_dir = output_dir.resolve().relative_to(output_manifest.parent.resolve())
    except ValueError:
        rel_dir = Path(os.path.relpath(output_dir, output_manifest.parent))
    audio_path = rel_dir / filename
    return audio_path.as_posix()


def clip_manifest_file(
    input_manifest: Path,
    output_manifest: Path,
    output_dir: Path,
    options: ClipOptions | None = None,
) -> TranscriptManifest:
    opts = options or ClipOptions()

    # B1: Format sanitization with allowlist
    fmt = opts.audio_format.strip("/\\\0")
    if fmt not in ALLOWED_FORMATS:
        raise ClippingError(
            f"invalid audio format: {opts.audio_format!r} "
            f"(allowed: {', '.join(sorted(ALLOWED_FORMATS))})"
        )

    manifest = load_manifest(input_manifest)

    source_path = Path(manifest.source_audio.path)

    # B2: Reject symlinks
    if source_path.is_symlink():
        raise ClippingError(
            f"source audio is a symlink, refusing to process: {source_path}"
        )

    # B2: Scope check — source audio must be within the manifest's directory tree
    try:
        source_path.resolve().relative_to(input_manifest.resolve().parent)
    except ValueError:
        raise ClippingError(
            f"source audio is outside the manifest directory: {source_path}"
        ) from None

    if not source_path.exists():
        raise ClippingError(f"source audio does not exist: {source_path}")

    ffmpeg = find_media_tool("ffmpeg", FFMPEG_ENV)
    if not ffmpeg.available or ffmpeg.path is None:
        raise ClippingError(
            "FFmpeg is not available. Install FFmpeg or set AUDAWISPR_FFMPEG."
        )
    ffmpeg_path = ffmpeg.path

    output_dir.mkdir(parents=True, exist_ok=True)

    duration_sec = manifest.source_audio.duration_seconds
    pad_before = opts.padding_before_ms / 1000.0
    pad_after = opts.padding_after_ms / 1000.0

    for idx, seg in enumerate(manifest.segments):
        padded_start = max(0.0, seg.start - pad_before)
        padded_end = seg.end + pad_after
        if duration_sec is not None:
            padded_end = min(padded_end, duration_sec)

        if padded_end <= padded_start:
            raise ClippingError(
                f"segment {seg.id} has zero or negative duration after padding"
            )

        filename = stable_snippet_filename(idx, seg.id, fmt)
        snippet_path = output_dir / filename

        # B1: Snippet path containment check
        try:
            snippet_path.resolve().relative_to(output_dir.resolve())
        except ValueError:
            raise ClippingError(
                f"snippet path escapes output directory: {snippet_path}"
            ) from None

        if not opts.force and snippet_path.exists() and snippet_path.stat().st_size > 0:
            # C4: Incremental save for skipped segment
            audio_file = _compute_audio_file(output_manifest, output_dir, filename)
            seg = seg.model_copy(update={"audio_file": audio_file})
            manifest.segments[idx] = seg
            save_manifest(manifest, output_manifest)
            continue

        try:
            result = subprocess.run(
                [
                    ffmpeg_path,
                    "-y",
                    "-ss",
                    f"{padded_start:.3f}",
                    "-t",
                    f"{padded_end - padded_start:.3f}",
                    "-i",
                    str(source_path),
                    "-b:a",
                    opts.bitrate,
                    str(snippet_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise ClippingError(f"FFmpeg timed out for segment {seg.id}") from None
        except OSError as exc:
            raise ClippingError(f"could not run FFmpeg: {exc}") from exc

        if result.returncode != 0:
            raise ClippingError(
                f"FFmpeg failed for segment {seg.id}: {result.stderr.strip()}"
            )

        if not snippet_path.exists() or snippet_path.stat().st_size == 0:
            raise ClippingError(f"FFmpeg produced empty snippet for segment {seg.id}")

        # C4: Incremental save after successful clip
        audio_file = _compute_audio_file(output_manifest, output_dir, filename)
        seg = seg.model_copy(update={"audio_file": audio_file})
        manifest.segments[idx] = seg
        save_manifest(manifest, output_manifest)

    return load_manifest(output_manifest)

"""One-shot pipeline orchestration over all phases."""

from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from audawispr.core.clipping import ClipOptions, clip_manifest_file
from audawispr.core.enrichment import EnrichmentOptions, enrich_manifest
from audawispr.core.errors import (
    CancelledError,
    ClippingError,
    EnrichmentError,
    ExportError,
    InputAudioError,
    ManifestError,
    OneShotError,
    SegmentationError,
    TranscriptionError,
)
from audawispr.core.export import ExportOptions, export_manifest_file
from audawispr.core.manifest import save_manifest
from audawispr.core.segmentation import SegmentationOptions, segment_manifest
from audawispr.core.transcription import TranscriptionOptions, transcribe_audio

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProgressEvent:
    """A progress notification emitted during pipeline execution."""

    phase: str
    message: str


ProgressHook = Callable[[ProgressEvent], None]


class CancellationToken:
    """Cooperative cancellation checked between phases."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def request_cancel(self) -> None:
        """Request cancellation of the pipeline run."""
        self._event.set()

    def check(self) -> None:
        """Raise CancelledError if cancellation was requested."""
        if self._event.is_set():
            raise CancelledError("pipeline run was cancelled")


@dataclass(frozen=True)
class PipelineRequest:
    """Configuration for a one-shot pipeline run."""

    audio: Path
    output: Path
    language: str = "fr"
    ipa: bool = False
    model_size: str = "small"
    device: str = "auto"
    compute_type: str = "int8"
    vad: bool = True
    pause_split_ms: int = 700
    min_duration_ms: int = 600
    max_duration_ms: int = 7000
    translation_provider: str = "none"
    deck_name: str | None = None
    keep_work: bool = False


@dataclass(frozen=True)
class PipelineResult:
    """Result of a completed pipeline run."""

    output_path: Path
    work_dir: Path


def _derive_work_dir(output: Path) -> Path:
    """Derive the work directory from the output path.

    When output is a file (has a suffix like .apkg), work dir is a sibling
    directory next to it. When output is a directory, work dir is nested.
    """
    # B4: Guard against work dir colliding with an existing directory
    # that shares the same stem as the output path.
    # Only applies to file outputs (output has a suffix).
    if output.suffix:
        existing = output.with_suffix("")
        work_dir = existing / "_work"
        if existing != work_dir and hasattr(existing, "is_dir") and existing.is_dir():
            raise ValueError(
                f"Output path {output} collides with existing directory {existing}"
            )
    else:
        work_dir = output / "_work"

    return work_dir


_MIN_FREE_SPACE = 500 * 1024 * 1024  # 500 MB
_WHISPER_CACHE_HINT = (
    Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "whisper"
)


def _check_disk_space(work_dir: Path) -> None:
    """Raise OneShotError if disk space on relevant volumes is too low."""
    # Check work-dir volume
    try:
        usage = shutil.disk_usage(work_dir)
    except OSError:
        pass
    else:
        if usage.free < _MIN_FREE_SPACE:
            raise OneShotError(
                f"Only {usage.free / (1024**3):.1f} GiB free on {work_dir}, "
                f"need at least {_MIN_FREE_SPACE / (1024**3):.1f} GiB"
            )
    # Check Whisper cache volume (first-run download is ~2 GB)
    try:
        cache_usage = shutil.disk_usage(_WHISPER_CACHE_HINT.parent)
    except OSError:
        pass
    else:
        if cache_usage.free < 3 * 1024**3:
            # Soft warning — cache may already be populated
            logger.warning(
                "Only %.1f GiB free on cache volume (%s); "
                "Whisper model download may fail if not already cached",
                cache_usage.free / (1024**3),
                _WHISPER_CACHE_HINT.parent,
            )


def run_pipeline(
    request: PipelineRequest,
    *,
    progress_hook: ProgressHook | None = None,
    cancellation_token: CancellationToken | None = None,
) -> PipelineResult:
    """Run the full audawispr pipeline in one shot.

    Phase order: transcribe -> segment -> enrich (conditional) -> clip -> export.
    """
    work_dir = _derive_work_dir(request.output)
    work_dir.mkdir(parents=True, exist_ok=True)
    _check_disk_space(work_dir)
    if work_dir.is_symlink():
        raise OneShotError(
            f"Work directory is a symlink, refusing to continue: {work_dir}"
        )

    def _emit(phase: str, message: str) -> None:
        if progress_hook is not None:
            progress_hook(ProgressEvent(phase=phase, message=message))

    def _check_cancel() -> None:
        if cancellation_token is not None:
            cancellation_token.check()

    success = False
    try:
        # Transcribe
        _check_cancel()
        _emit("transcribe", "Transcribing audio...")
        transcription_options = TranscriptionOptions(
            language=request.language,
            model_size=request.model_size,
            device=request.device,
            compute_type=request.compute_type,
            vad=request.vad,
        )
        try:
            manifest = transcribe_audio(request.audio, transcription_options)
            transcript_path = work_dir / "transcript.json"
            save_manifest(manifest, transcript_path)
        except (TranscriptionError, InputAudioError) as exc:
            raise OneShotError(
                f"Transcription failed: {exc}. "
                "Try a different --model-size or --device."
            ) from exc
        except ManifestError as exc:
            raise OneShotError(
                f"Transcription failed: {exc}. "
                "Check that the manifest is valid and disk is not full."
            ) from exc

        # Segment
        _check_cancel()
        _emit("segment", "Segmenting transcript...")
        segmentation_options = SegmentationOptions(
            pause_split_ms=request.pause_split_ms,
            min_duration_ms=request.min_duration_ms,
            max_duration_ms=request.max_duration_ms,
            merge_short=True,
        )
        try:
            manifest = segment_manifest(manifest, segmentation_options)
            segments_path = work_dir / "segments.json"
            save_manifest(manifest, segments_path)
        except SegmentationError as exc:
            raise OneShotError(
                f"Segmentation failed: {exc}. "
                "Check your audio quality or adjust --pause-split-ms."
            ) from exc
        except ManifestError as exc:
            raise OneShotError(
                f"Segmentation failed: {exc}. "
                "Check that the manifest is valid and disk is not full."
            ) from exc

        # Enrich (conditional)
        enrichment_happened = False
        if request.ipa or request.translation_provider != "none":
            _check_cancel()
            _emit("enrich", "Enriching segments...")
            enrichment_options = EnrichmentOptions(
                ipa=request.ipa,
                translation_provider=request.translation_provider,
            )
            try:
                manifest = enrich_manifest(manifest, enrichment_options)
                enriched_path = work_dir / "enriched.json"
                save_manifest(manifest, enriched_path)
                enrichment_happened = True
            except EnrichmentError as exc:
                raise OneShotError(
                    f"Enrichment failed: {exc}. Check --language or disable --ipa."
                ) from exc
            except ManifestError as exc:
                raise OneShotError(
                    f"Enrichment failed: {exc}. "
                    "Check that the manifest is valid and disk is not full."
                ) from exc

        # Clip
        _check_cancel()
        _emit("clip", "Clipping audio snippets...")
        clip_input_path = (
            work_dir / "enriched.json"
            if enrichment_happened
            else work_dir / "segments.json"
        )
        clipped_path = work_dir / "clipped.json"
        media_dir = work_dir / "media"
        try:
            clip_manifest_file(
                clip_input_path,
                clipped_path,
                media_dir,
                ClipOptions(),
            )
        except ClippingError as exc:
            raise OneShotError(
                f"Clipping failed: {exc}. "
                "Check that FFmpeg is installed and the source audio is valid."
            ) from exc
        except ManifestError as exc:
            raise OneShotError(
                f"Clipping failed: {exc}. "
                "Check that the manifest is valid and disk is not full."
            ) from exc

        # Export
        _check_cancel()
        _emit("export", "Exporting to final format...")
        export_format = "apkg" if request.output.suffix == ".apkg" else "anki-csv"
        export_options = ExportOptions(
            format=export_format,
            deck_name=request.deck_name,
        )
        try:
            export_manifest_file(clipped_path, request.output, export_options)
        except ExportError as exc:
            raise OneShotError(
                f"Export failed: {exc}. Check the output path and available disk space."
            ) from exc
        except ManifestError as exc:
            raise OneShotError(
                f"Export failed: {exc}. "
                "Check that the manifest is valid and disk is not full."
            ) from exc

        success = True
        return PipelineResult(
            output_path=request.output,
            work_dir=work_dir,
        )
    except CancelledError:
        raise
    finally:
        # C1: Explicit cancellation check (belt-and-suspenders)
        exc_info = sys.exc_info()
        is_cancelled = exc_info[1] is not None and isinstance(
            exc_info[1], CancelledError
        )

        if not is_cancelled and success and not request.keep_work and work_dir.exists():
            # C2: Symlink safety — recursively unlink all symlinks at every
            # depth before cleanup, preventing shutil.rmtree from following them.
            def _remove_symlinks(path: Path) -> int:
                count = 0
                for entry in path.rglob("*"):
                    try:
                        if entry.is_symlink():
                            entry.unlink()
                            count += 1
                    except OSError:
                        pass
                return count

            linked = _remove_symlinks(work_dir)
            if linked:
                logger.warning(
                    "Removed %d symlink(s) from work directory before cleanup",
                    linked,
                )

            shutil.rmtree(work_dir, ignore_errors=True)

        # C5: Emit work dir path to stderr on failure
        if not success and work_dir.exists():
            sys.stderr.write(f"Work directory preserved at: {work_dir}\n")

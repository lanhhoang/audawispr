"""One-shot pipeline orchestration over all phases."""

from __future__ import annotations

import shutil
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
    if output.suffix:
        return output.with_suffix("") / "_work"
    return output / "_work"


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
        except (TranscriptionError, InputAudioError, ManifestError) as exc:
            raise OneShotError(
                f"Transcription failed: {exc}. "
                "Try a different --model-size or --device."
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
        except (SegmentationError, ManifestError) as exc:
            raise OneShotError(
                f"Segmentation failed: {exc}. "
                "Check your audio quality or adjust --pause-split-ms."
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
            except (EnrichmentError, ManifestError) as exc:
                raise OneShotError(
                    f"Enrichment failed: {exc}. Check --language or disable --ipa."
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
        except (ClippingError, ManifestError) as exc:
            raise OneShotError(
                f"Clipping failed: {exc}. "
                "Check that FFmpeg is installed and the source audio is valid."
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
        except (ExportError, ManifestError) as exc:
            raise OneShotError(
                f"Export failed: {exc}. Check the output path and available disk space."
            ) from exc

        success = True
        return PipelineResult(
            output_path=request.output,
            work_dir=work_dir,
        )
    except CancelledError:
        raise
    finally:
        if success and not request.keep_work and work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)

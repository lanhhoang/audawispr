"""Reusable core services for audawispr."""

from audawispr.core.audio import collect_source_audio_metadata
from audawispr.core.clipping import ClipOptions, clip_manifest_file
from audawispr.core.enrichment import (
    EnrichmentOptions,
    enrich_manifest,
    enrich_manifest_file,
)
from audawispr.core.manifest import TranscriptManifest, load_manifest, save_manifest
from audawispr.core.segmentation import (
    SegmentationOptions,
    default_inspection_tsv_path,
    save_inspection_tsv,
    segment_manifest,
)
from audawispr.core.transcription import TranscriptionOptions, transcribe_audio

__all__ = [
    "ClipOptions",
    "EnrichmentOptions",
    "SegmentationOptions",
    "TranscriptManifest",
    "TranscriptionOptions",
    "clip_manifest_file",
    "collect_source_audio_metadata",
    "default_inspection_tsv_path",
    "enrich_manifest",
    "enrich_manifest_file",
    "load_manifest",
    "save_inspection_tsv",
    "save_manifest",
    "segment_manifest",
    "transcribe_audio",
]

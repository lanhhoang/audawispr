"""audawispr package."""

from audawispr.__about__ import __version__
from audawispr.core.errors import (
    AudawisprError,
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
from audawispr.pipeline import Pipeline

__all__ = [
    "__version__",
    "AudawisprError",
    "CancelledError",
    "ClippingError",
    "EnrichmentError",
    "ExportError",
    "InputAudioError",
    "ManifestError",
    "OneShotError",
    "Pipeline",
    "SegmentationError",
    "TranscriptionError",
]

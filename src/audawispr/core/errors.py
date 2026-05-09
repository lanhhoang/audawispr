"""Shared audawispr core exceptions."""

from __future__ import annotations


class AudawisprError(Exception):
    """Base class for expected audawispr runtime failures."""


class InputAudioError(AudawisprError):
    """Raised when source audio cannot be used."""


class TranscriptionError(AudawisprError):
    """Raised when local transcription cannot produce a valid manifest."""


class SegmentationError(AudawisprError):
    """Raised when transcript segments cannot be rebuilt."""


class EnrichmentError(AudawisprError):
    """Raised when linguistic enrichment cannot be applied."""


class ManifestError(AudawisprError):
    """Raised when a manifest cannot be loaded, saved, or validated."""


class ClippingError(AudawisprError):
    """Raised when audio clipping cannot produce valid snippets."""


class ExportError(AudawisprError):
    """Raised when manifest export cannot produce valid output."""


class CancelledError(AudawisprError):
    """Raised when a pipeline run is cooperatively cancelled."""


class OneShotError(AudawisprError):
    """Raised when the one-shot pipeline cannot complete."""


class DependencyError(AudawisprError):
    """Raised when a required external dependency cannot be found or installed."""

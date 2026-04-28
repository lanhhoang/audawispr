"""Shared audawispr core exceptions."""


class AudawisprError(Exception):
    """Base class for expected audawispr runtime failures."""


class InputAudioError(AudawisprError):
    """Raised when source audio cannot be used."""


class TranscriptionError(AudawisprError):
    """Raised when local transcription cannot produce a valid manifest."""


class ManifestError(AudawisprError):
    """Raised when a manifest cannot be loaded, saved, or validated."""

from audawispr.core import (
    TranscriptionOptions,
    TranscriptManifest,
    collect_source_audio_metadata,
    load_manifest,
    save_manifest,
    transcribe_audio,
)


def test_phase_2_core_exports_are_importable() -> None:
    assert TranscriptManifest.__name__ == "TranscriptManifest"
    assert TranscriptionOptions().language == "fr"
    assert callable(collect_source_audio_metadata)
    assert callable(load_manifest)
    assert callable(save_manifest)
    assert callable(transcribe_audio)

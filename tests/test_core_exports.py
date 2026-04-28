from audawispr.core import (
    SegmentationOptions,
    TranscriptionOptions,
    TranscriptManifest,
    collect_source_audio_metadata,
    default_inspection_tsv_path,
    load_manifest,
    save_inspection_tsv,
    save_manifest,
    segment_manifest,
    transcribe_audio,
)


def test_core_exports_are_importable() -> None:
    assert TranscriptManifest.__name__ == "TranscriptManifest"
    assert TranscriptionOptions().language == "fr"
    assert SegmentationOptions().pause_split_ms == 700
    assert callable(collect_source_audio_metadata)
    assert callable(default_inspection_tsv_path)
    assert callable(load_manifest)
    assert callable(save_inspection_tsv)
    assert callable(save_manifest)
    assert callable(segment_manifest)
    assert callable(transcribe_audio)

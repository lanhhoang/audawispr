from audawispr.core import (
    ClipOptions,
    EnrichmentOptions,
    SegmentationOptions,
    TranscriptionOptions,
    TranscriptManifest,
    clip_manifest_file,
    collect_source_audio_metadata,
    default_inspection_tsv_path,
    enrich_manifest,
    enrich_manifest_file,
    load_manifest,
    save_inspection_tsv,
    save_manifest,
    segment_manifest,
    transcribe_audio,
)


def test_core_exports_are_importable() -> None:
    assert TranscriptManifest.__name__ == "TranscriptManifest"
    assert EnrichmentOptions().translation_provider == "none"
    assert TranscriptionOptions().language == "fr"
    assert SegmentationOptions().pause_split_ms == 700
    assert callable(collect_source_audio_metadata)
    assert callable(default_inspection_tsv_path)
    assert callable(enrich_manifest)
    assert callable(enrich_manifest_file)
    assert callable(load_manifest)
    assert callable(save_inspection_tsv)
    assert callable(save_manifest)
    assert callable(segment_manifest)
    assert callable(transcribe_audio)
    assert ClipOptions().audio_format == "mp3"
    assert callable(clip_manifest_file)

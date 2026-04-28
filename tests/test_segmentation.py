from pathlib import Path

import pytest

from audawispr.core.errors import SegmentationError
from audawispr.core.manifest import (
    SourceAudio,
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
    load_manifest,
    save_manifest,
)
from audawispr.core.segmentation import (
    SegmentationOptions,
    default_inspection_tsv_path,
    save_inspection_tsv,
    segment_manifest,
)


def test_segment_manifest_splits_on_sentence_punctuation() -> None:
    manifest = _make_manifest(
        [
            _word("Bonjour.", 0.0, 0.7),
            _word("Comment", 0.8, 1.1),
            _word("allez-vous?", 1.2, 1.8),
        ]
    )

    segmented = segment_manifest(manifest, SegmentationOptions())

    assert [segment.text for segment in segmented.segments] == [
        "Bonjour.",
        "Comment allez-vous?",
    ]
    assert [segment.id for segment in segmented.segments] == ["seg-0000", "seg-0001"]


def test_segment_manifest_splits_on_pause_threshold() -> None:
    manifest = _make_manifest(
        [
            _word("Bonjour", 0.0, 0.7),
            _word("encore", 1.4, 1.9),
        ]
    )

    segmented = segment_manifest(
        manifest,
        SegmentationOptions(pause_split_ms=700, merge_short=False),
    )

    assert [segment.text for segment in segmented.segments] == ["Bonjour", "encore"]


def test_segment_manifest_splits_on_max_duration() -> None:
    manifest = _make_manifest(
        [
            _word("un", 0.0, 0.4),
            _word("deux", 0.5, 0.9),
            _word("trois", 1.0, 1.4),
        ]
    )

    segmented = segment_manifest(
        manifest,
        SegmentationOptions(max_duration_ms=1000, merge_short=False),
    )

    assert [segment.text for segment in segmented.segments] == ["un deux", "trois"]
    assert segmented.segments[0].end - segmented.segments[0].start <= 1.0


def test_segment_manifest_merges_short_segments_without_exceeding_max() -> None:
    manifest = _make_manifest(
        [
            _word("Oui.", 0.0, 0.2),
            _word("Bonjour.", 0.3, 0.9),
            _word("Merci.", 1.0, 1.2),
        ]
    )

    segmented = segment_manifest(
        manifest,
        SegmentationOptions(min_duration_ms=600, max_duration_ms=1000),
    )

    assert [segment.text for segment in segmented.segments] == [
        "Oui. Bonjour.",
        "Merci.",
    ]


def test_segment_manifest_rejects_invalid_options() -> None:
    with pytest.raises(SegmentationError, match="max_duration_ms"):
        SegmentationOptions(min_duration_ms=1000, max_duration_ms=500)


def test_segment_manifest_rejects_invalid_word_timestamps() -> None:
    manifest = _make_manifest(
        [
            _word("Bonjour", 0.0, 0.8),
            _word("encore", 0.7, 1.0),
        ]
    )

    with pytest.raises(SegmentationError, match="non-overlapping"):
        segment_manifest(manifest)


def test_segment_manifest_rejects_non_finite_word_timestamps() -> None:
    manifest = _make_manifest([_word("Bonjour", 0.0, float("inf"))])

    with pytest.raises(SegmentationError, match="finite"):
        segment_manifest(manifest)


def test_segmented_manifest_stays_valid_after_save_round_trip(tmp_path: Path) -> None:
    output = tmp_path / "segments.json"
    manifest = _make_manifest(
        [
            _word("Bonjour.", 0.0, 0.7),
            _word("Encore.", 0.8, 1.4),
        ]
    )

    segmented = segment_manifest(manifest)
    save_manifest(segmented, output)
    loaded = load_manifest(output)

    assert isinstance(loaded, TranscriptManifest)
    assert loaded.source_audio == manifest.source_audio
    assert loaded.transcription == manifest.transcription
    assert [segment.text for segment in loaded.segments] == ["Bonjour.", "Encore."]


def test_save_inspection_tsv_writes_expected_shape(tmp_path: Path) -> None:
    output = tmp_path / "segments.tsv"
    manifest = segment_manifest(
        _make_manifest(
            [
                _word("Bonjour.", 0.0, 0.7),
                _word("Ligne\navec\tblanc.", 0.8, 1.5),
            ]
        )
    )

    save_inspection_tsv(manifest, output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "id\tindex\tstart\tend\ttext",
        "seg-0000\t0\t0.000\t0.700\tBonjour.",
        "seg-0001\t1\t0.800\t1.500\tLigne avec blanc.",
    ]


def test_default_inspection_tsv_path_uses_output_stem(tmp_path: Path) -> None:
    assert default_inspection_tsv_path(tmp_path / "nested" / "segments.json") == (
        tmp_path / "nested" / "segments.tsv"
    )


def _make_manifest(words: list[TranscriptWord]) -> TranscriptManifest:
    return TranscriptManifest(
        language="fr",
        source_audio=SourceAudio(
            file_name="lesson.mp3",
            path="/tmp/lesson.mp3",
            size_bytes=3,
            sha256="0" * 64,
            language="fr",
        ),
        transcription=TranscriptionSettings(
            model_size="small",
            device="auto",
            compute_type="int8",
            vad=True,
        ),
        segments=[
            TranscriptSegment(
                id="seg-0000",
                start=words[0].start,
                end=words[-1].end,
                text=" ".join(word.text for word in words),
                words=words,
            )
        ],
    )


def _word(text: str, start: float, end: float) -> TranscriptWord:
    return TranscriptWord(text=text, start=start, end=end)

import json
from pathlib import Path

import pytest

from audawispr.core.errors import ManifestError
from audawispr.core.manifest import (
    SourceAudio,
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
    load_manifest,
    save_manifest,
)


def make_manifest() -> TranscriptManifest:
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
                start=0.0,
                end=1.0,
                text="Bonjour.",
                words=[
                    TranscriptWord(
                        text="Bonjour",
                        start=0.0,
                        end=0.8,
                        probability=0.95,
                    )
                ],
            )
        ],
    )


def test_save_and_load_manifest_round_trip(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "transcript.json"
    manifest = make_manifest()

    save_manifest(manifest, output)
    loaded = load_manifest(output)

    assert loaded.schema_version == "1.0"
    assert loaded.language == "fr"
    assert loaded.source_audio.sha256 == "0" * 64
    assert loaded.segments[0].words[0].text == "Bonjour"


def test_load_manifest_rejects_malformed_json(tmp_path: Path) -> None:
    manifest_path = tmp_path / "bad.json"
    manifest_path.write_text("{", encoding="utf-8")

    with pytest.raises(ManifestError, match="not valid JSON"):
        load_manifest(manifest_path)


def test_load_manifest_rejects_non_monotonic_segments(tmp_path: Path) -> None:
    payload = make_manifest().model_dump(mode="json")
    payload["segments"].append(
        {
            "id": "seg-0001",
            "start": 0.5,
            "end": 1.5,
            "text": "Encore.",
            "words": [{"text": "Encore", "start": 0.5, "end": 1.0}],
        }
    )
    manifest_path = tmp_path / "bad-timing.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ManifestError, match="non-overlapping"):
        load_manifest(manifest_path)


def test_load_manifest_rejects_missing_word_timestamps(tmp_path: Path) -> None:
    payload = make_manifest().model_dump(mode="json")
    payload["segments"][0]["words"] = []
    manifest_path = tmp_path / "missing-words.json"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ManifestError):
        load_manifest(manifest_path)

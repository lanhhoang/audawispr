from dataclasses import dataclass
from pathlib import Path

import pytest

from audawispr.core.errors import TranscriptionError
from audawispr.core.manifest import TranscriptSegment, TranscriptWord
from audawispr.core.transcription import (
    TranscriptionOptions,
    _convert_segment,
    transcribe_audio,
)


class FakeBackend:
    def transcribe(
        self,
        audio_path: Path,
        options: TranscriptionOptions,
    ) -> list[TranscriptSegment]:
        assert audio_path.exists()
        assert options.language == "fr"
        return [
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
                    )
                ],
            )
        ]


@dataclass(frozen=True)
class RawWord:
    word: str
    start: float
    end: float
    probability: float | None = None


@dataclass(frozen=True)
class RawSegment:
    id: int
    start: float
    end: float
    text: str
    words: list[RawWord] | None


def test_transcribe_audio_with_fake_backend(tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")

    manifest = transcribe_audio(
        audio_path,
        TranscriptionOptions(),
        backend=FakeBackend(),
    )

    assert manifest.language == "fr"
    assert manifest.source_audio.file_name == "lesson.mp3"
    assert manifest.source_audio.size_bytes == 3
    assert manifest.transcription.model_size == "small"
    assert manifest.transcription.word_timestamps is True
    assert manifest.segments[0].words[0].text == "Bonjour"


def test_convert_segment_rejects_missing_word_timestamps() -> None:
    segment = RawSegment(
        id=0,
        start=0.0,
        end=1.0,
        text="Bonjour.",
        words=None,
    )

    with pytest.raises(TranscriptionError, match="missing word timestamps"):
        _convert_segment(0, segment)

from pathlib import Path

import pytest

from audawispr.core import audio
from audawispr.core.errors import InputAudioError


def test_collect_source_audio_metadata_fields(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    monkeypatch.setattr(audio, "_read_duration_seconds", lambda _: None)

    metadata = audio.collect_source_audio_metadata(audio_path, "fr")

    assert metadata.file_name == "lesson.mp3"
    assert metadata.path == str(audio_path.resolve())
    assert metadata.size_bytes == 3
    assert metadata.sha256 == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )
    assert metadata.language == "fr"
    assert metadata.duration_seconds is None


def test_collect_source_audio_metadata_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(InputAudioError, match="does not exist"):
        audio.collect_source_audio_metadata(tmp_path / "missing.mp3", "fr")

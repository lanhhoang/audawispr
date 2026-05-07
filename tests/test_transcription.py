from dataclasses import dataclass
from pathlib import Path

import pytest

from audawispr.core.errors import DependencyError, TranscriptionError
from audawispr.core.manifest import TranscriptSegment, TranscriptWord
from audawispr.core.transcription import (
    TranscriptionOptions,
    _convert_segment,
    download_whisper_model,
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


def test_download_whisper_model_calls_snapshot_download(monkeypatch):
    """Verify the correct repo_id and allow_patterns are passed."""
    import huggingface_hub as hf

    calls = []

    def fake_snapshot_download(repo_id, **kwargs):
        calls.append((repo_id, kwargs))
        return f"/fake/cache/{repo_id}"

    monkeypatch.setattr(hf, "snapshot_download", fake_snapshot_download)
    # Also prevent the cache pre-check from short-circuiting
    monkeypatch.setattr(
        "faster_whisper.utils.download_model",
        lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("not cached")),
    )

    result = download_whisper_model("small")

    assert len(calls) == 1
    repo_id, kwargs = calls[0]
    assert repo_id == "Systran/faster-whisper-small"
    assert "allow_patterns" in kwargs
    assert kwargs.get("tqdm_class") is None
    assert result == "/fake/cache/Systran/faster-whisper-small"


def test_download_whisper_model_accepts_repo_id_directly(monkeypatch):
    import huggingface_hub as hf

    calls = []
    monkeypatch.setattr(
        hf,
        "snapshot_download",
        lambda repo_id, **kw: calls.append(repo_id) or f"/path/{repo_id}",
    )

    download_whisper_model("custom/model-id")
    assert "custom/model-id" in calls


def test_download_whisper_model_invalid_size_raises_value_error():

    with pytest.raises(ValueError, match="Unknown model size"):
        download_whisper_model("nonexistent-size")


def test_download_whisper_model_raises_dependency_error_on_failure(monkeypatch):
    import huggingface_hub as hf

    monkeypatch.setattr(
        hf,
        "snapshot_download",
        lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("timeout")),
    )

    with pytest.raises(DependencyError, match="Failed to download"):
        download_whisper_model("small")


def test_download_whisper_model_skips_when_cached(monkeypatch):
    """With force=False, cached model returns path without calling snapshot_download."""
    import huggingface_hub as hf

    calls = []

    monkeypatch.setattr(
        "faster_whisper.utils.download_model",
        lambda size, local_files_only=True: f"/cache/{size}/snapshots/hash",
    )
    monkeypatch.setattr(hf, "snapshot_download", lambda *a, **kw: calls.append(1))

    result = download_whisper_model("small")

    assert len(calls) == 0  # snapshot_download NOT called
    assert "snapshots" in result


def test_download_whisper_model_force_re_downloads(monkeypatch, tmp_path):
    """With force=True, cached model is deleted and re-downloaded."""
    import huggingface_hub as hf

    # Create a fake cache snapshot inside a HuggingFace-style cache hierarchy
    cache_dir = (
        tmp_path
        / ".cache"
        / "huggingface"
        / "models--Systran--faster-whisper-small"
        / "snapshots"
        / "abc123"
    )
    cache_dir.mkdir(parents=True)
    (cache_dir / "model.bin").write_bytes(b"fake")

    # First call returns cached path, second raises (not found — already deleted)
    call_count = 0

    def fake_fw_download(size, local_files_only=True):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return str(cache_dir)
        raise FileNotFoundError("not found")

    monkeypatch.setattr(
        "faster_whisper.utils.download_model",
        fake_fw_download,
    )

    dl_calls = []
    monkeypatch.setattr(
        hf,
        "snapshot_download",
        lambda *a, **kw: dl_calls.append(1) or "/new/cache/path",
    )

    result = download_whisper_model("small", force=True)

    assert len(dl_calls) == 1  # snapshot_download was called
    assert not cache_dir.exists()  # old cache was deleted
    assert result == "/new/cache/path"

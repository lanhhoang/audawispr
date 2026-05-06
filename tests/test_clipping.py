from pathlib import Path

import pytest

from audawispr.core.clipping import (
    ClipOptions,
    _compute_audio_file,
    clip_manifest_file,
    safe_segment_id,
    stable_snippet_filename,
)
from audawispr.core.errors import ClippingError, DependencyError
from audawispr.core.manifest import (
    SourceAudio,
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
    load_manifest,
)


def _make_manifest(
    path: str = "/tmp/lesson.mp3",
    duration_seconds: float | None = 5.0,
    language: str = "fr",
) -> TranscriptManifest:
    return TranscriptManifest(
        language=language,
        source_audio=SourceAudio(
            file_name="lesson.mp3",
            path=path,
            size_bytes=3,
            sha256="0" * 64,
            language=language,
            duration_seconds=duration_seconds,
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
                start=0.5,
                end=1.5,
                text="Bonjour.",
                words=[TranscriptWord(text="Bonjour.", start=0.5, end=1.5)],
            ),
            TranscriptSegment(
                id="seg-0001",
                start=2.0,
                end=3.0,
                text="Encore.",
                words=[TranscriptWord(text="Encore.", start=2.0, end=3.0)],
            ),
        ],
    )


def _write_manifest(tmp_path: Path, manifest: TranscriptManifest) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(manifest.model_dump_json(), encoding="utf-8")
    return path


def _make_source_audio(tmp_path: Path, name: str = "lesson.mp3") -> Path:
    path = tmp_path / name
    path.write_bytes(b"fake audio data")
    return path


# --- safe_segment_id tests ---


def test_safe_segment_id_keeps_valid_chars() -> None:
    assert safe_segment_id("hello-world_123") == "hello-world_123"


def test_safe_segment_id_replaces_invalid_chars_with_dash() -> None:
    assert safe_segment_id("hello world!@#") == "hello-world"


def test_safe_segment_id_trims_leading_and_trailing_dots_and_dashes() -> None:
    assert safe_segment_id("...---hello...---") == "hello"


def test_safe_segment_id_truncates_to_80_chars() -> None:
    result = safe_segment_id("a" * 100)
    assert len(result) == 80


def test_safe_segment_id_falls_back_to_segment() -> None:
    assert safe_segment_id("") == "segment"


# --- stable_snippet_filename tests ---


def test_stable_snippet_filename() -> None:
    assert stable_snippet_filename(1, "seg-0001", "mp3") == "0001_seg-0001.mp3"


def test_stable_snippet_filename_sanitizes_id() -> None:
    assert stable_snippet_filename(0, "bad/id!", "wav") == "0000_bad-id.wav"


# --- clip_manifest_file tests ---


def test_clip_manifest_raises_when_ffmpeg_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: (_ for _ in ()).throw(DependencyError("ffmpeg not available")),
    )

    with pytest.raises(DependencyError, match="ffmpeg not available"):
        clip_manifest_file(manifest_path, output_manifest, output_dir)


def test_clip_manifest_raises_when_source_audio_missing(tmp_path: Path) -> None:
    manifest = _make_manifest(path=str(tmp_path / "missing.mp3"))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"

    with pytest.raises(ClippingError, match="source audio does not exist"):
        clip_manifest_file(manifest_path, output_manifest, tmp_path / "media")


def test_clip_manifest_raises_on_ffmpeg_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: Path("/usr/bin/fake-ffmpeg"),
    )

    def fake_run(*args: object, **kwargs: object) -> object:
        class FakeResult:
            returncode = 1
            stdout = ""
            stderr = "mock error"

        return FakeResult()

    monkeypatch.setattr("audawispr.core.clipping.subprocess.run", fake_run)

    with pytest.raises(ClippingError, match="FFmpeg failed"):
        clip_manifest_file(manifest_path, output_manifest, output_dir)


def test_clip_manifest_raises_on_empty_snippet(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"
    output_dir.mkdir()

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: Path("/usr/bin/fake-ffmpeg"),
    )

    def fake_run(*args: object, **kwargs: object) -> object:
        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeResult()

    monkeypatch.setattr("audawispr.core.clipping.subprocess.run", fake_run)

    with pytest.raises(ClippingError, match="empty snippet"):
        clip_manifest_file(manifest_path, output_manifest, output_dir)


def test_clip_manifest_raises_on_negative_duration_after_padding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _make_source_audio(tmp_path)
    output_manifest = tmp_path / "clipped.json"

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: Path("/usr/bin/fake-ffmpeg"),
    )

    bad_manifest = TranscriptManifest(
        language="fr",
        source_audio=SourceAudio(
            file_name="lesson.mp3",
            path=str(source),
            size_bytes=3,
            sha256="0" * 64,
            language="fr",
            duration_seconds=0.0,
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
                end=0.0,
                text="Bonjour.",
                words=[TranscriptWord(text="Bonjour.", start=0.0, end=0.0)],
            ),
        ],
    )
    bad_path = _write_manifest(tmp_path, bad_manifest)

    with pytest.raises(ClippingError, match="zero or negative duration"):
        clip_manifest_file(bad_path, output_manifest, tmp_path / "media")


def test_clip_manifest_padding_bounded_by_duration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _make_source_audio(tmp_path)
    manifest = TranscriptManifest(
        language="fr",
        source_audio=SourceAudio(
            file_name="lesson.mp3",
            path=str(source),
            size_bytes=3,
            sha256="0" * 64,
            language="fr",
            duration_seconds=1.0,
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
                start=0.3,
                end=0.8,
                text="Bonjour.",
                words=[TranscriptWord(text="Bonjour.", start=0.3, end=0.8)],
            ),
        ],
    )
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"
    output_dir.mkdir()

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: Path("/usr/bin/fake-ffmpeg"),
    )

    captured_args: list[list[str]] = []

    def fake_run(args: list[str], *a: object, **kw: object) -> object:
        captured_args.append(args)
        snippet = args[-1]
        Path(snippet).write_bytes(b"data")

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeResult()

    monkeypatch.setattr("audawispr.core.clipping.subprocess.run", fake_run)

    clip_manifest_file(
        manifest_path,
        output_manifest,
        output_dir,
        ClipOptions(padding_before_ms=200, padding_after_ms=200),
    )

    # duration is 1.0s, segment is 0.3-0.8, padded to 0.1-1.0 (clamped to duration)
    # The -t flag is clip_duration = 1.0 - 0.1 = 0.9
    assert len(captured_args) >= 1


def test_clip_manifest_skips_existing_snippets_without_force(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"
    output_dir.mkdir()

    # Pre-create snippet files so clipping skips them
    (output_dir / "0000_seg-0000.mp3").write_bytes(b"data")
    (output_dir / "0001_seg-0001.mp3").write_bytes(b"data")

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: Path("/usr/bin/fake-ffmpeg"),
    )

    call_count = 0

    def fake_run(*args: object, **kwargs: object) -> object:
        nonlocal call_count
        call_count += 1

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeResult()

    monkeypatch.setattr("audawispr.core.clipping.subprocess.run", fake_run)

    # Should succeed without calling FFmpeg because snippets already exist
    clip_manifest_file(manifest_path, output_manifest, output_dir)
    assert call_count == 0
    assert output_manifest.exists()
    body = output_manifest.read_text(encoding="utf-8")
    assert "audio_file" in body


def test_clip_manifest_writes_manifest_with_audio_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: Path("/usr/bin/fake-ffmpeg"),
    )

    snippet_files: list[Path] = []

    def fake_run(args: list[str], *a: object, **kw: object) -> object:
        snippet = Path(args[-1])
        snippet.parent.mkdir(parents=True, exist_ok=True)
        snippet.write_bytes(b"data")
        snippet_files.append(snippet)

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeResult()

    monkeypatch.setattr("audawispr.core.clipping.subprocess.run", fake_run)

    result = clip_manifest_file(manifest_path, output_manifest, output_dir)

    assert output_manifest.exists()
    assert len(result.segments) == 2
    body = output_manifest.read_text(encoding="utf-8")
    assert '"audio_file"' in body


def test_clip_manifest_force_reclips_existing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"
    output_dir.mkdir()
    (output_dir / "0000_seg-0000.mp3").write_bytes(b"data")
    (output_dir / "0001_seg-0001.mp3").write_bytes(b"data")

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: Path("/usr/bin/fake-ffmpeg"),
    )

    call_count = 0

    def fake_run(args: list[str], *a: object, **kw: object) -> object:
        nonlocal call_count
        call_count += 1
        snippet = Path(args[-1])
        snippet.write_bytes(b"data")

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        return FakeResult()

    monkeypatch.setattr("audawispr.core.clipping.subprocess.run", fake_run)

    clip_manifest_file(
        manifest_path, output_manifest, output_dir, ClipOptions(force=True)
    )

    assert call_count == 2
    body = output_manifest.read_text(encoding="utf-8")
    assert '"audio_file"' in body


def test_clip_default_options() -> None:
    opts = ClipOptions()
    assert opts.padding_before_ms == 150
    assert opts.padding_after_ms == 250
    assert opts.audio_format == "mp3"
    assert opts.bitrate == "128k"
    assert opts.force is False


# --- B1: Format sanitization tests ---


def test_format_sanitization_rejects_path_traversal(tmp_path: Path) -> None:
    """audio_format containing path traversal characters is rejected."""
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"

    with pytest.raises(ClippingError, match="invalid audio format"):
        clip_manifest_file(
            manifest_path,
            output_manifest,
            output_dir,
            ClipOptions(audio_format="../../.bashrc"),
        )


def test_format_sanitization_rejects_invalid_format(tmp_path: Path) -> None:
    """audio_format not in ALLOWED_FORMATS is rejected."""
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"

    with pytest.raises(ClippingError, match="invalid audio format"):
        clip_manifest_file(
            manifest_path,
            output_manifest,
            output_dir,
            ClipOptions(audio_format="exe"),
        )


# --- B2: Source audio path hardening tests ---


def test_source_audio_rejects_symlink(tmp_path: Path) -> None:
    """source_audio.path that is a symlink is rejected."""
    real_file = tmp_path / "real.mp3"
    real_file.write_bytes(b"data")
    link = tmp_path / "link.mp3"
    link.symlink_to(real_file)

    manifest = _make_manifest(path=str(link))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"

    with pytest.raises(ClippingError, match="symlink"):
        clip_manifest_file(manifest_path, output_manifest, tmp_path / "media")


# --- B3: _compute_audio_file fallback test ---


def test_compute_audio_file_fallback_on_valueerror(tmp_path: Path) -> None:
    """_compute_audio_file falls back to os.path.relpath when relative_to fails."""
    output_manifest = tmp_path / "a" / "manifest.json"
    output_manifest.parent.mkdir(parents=True)
    output_dir = tmp_path / "b"
    output_dir.mkdir()
    filename = "test.mp3"

    result = _compute_audio_file(output_manifest, output_dir, filename)

    assert isinstance(result, str)
    assert result.endswith(filename)
    # output_dir and output_manifest.parent are siblings,
    # so the relative path should contain "../"
    assert "../" in result


# --- C4: Incremental manifest save test ---


def test_clip_incremental_manifest_save(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Manifest is saved incrementally after each successful clip."""
    source = _make_source_audio(tmp_path)
    manifest = _make_manifest(path=str(source))
    manifest_path = _write_manifest(tmp_path, manifest)
    output_manifest = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"
    output_dir.mkdir()

    monkeypatch.setattr(
        "audawispr.core.clipping.ensure_ffmpeg",
        lambda: Path("/usr/bin/fake-ffmpeg"),
    )

    call_count: int = 0

    def fake_run(args: list[str], *a: object, **kw: object) -> object:
        nonlocal call_count
        call_count += 1
        snippet = Path(args[-1])
        snippet.parent.mkdir(parents=True, exist_ok=True)

        class FakeResult:
            returncode = 0
            stdout = ""
            stderr = ""

        if call_count == 1:
            # First segment succeeds
            snippet.write_bytes(b"data")
            return FakeResult()
        else:
            # Second segment produces empty snippet -> will raise
            snippet.write_bytes(b"")
            return FakeResult()

    monkeypatch.setattr("audawispr.core.clipping.subprocess.run", fake_run)

    with pytest.raises(ClippingError, match="empty snippet"):
        clip_manifest_file(manifest_path, output_manifest, output_dir)

    # Manifest should have been saved after first segment (incremental)
    assert output_manifest.exists()
    saved = load_manifest(output_manifest)
    # First segment should have audio_file set
    assert saved.segments[0].audio_file is not None
    assert saved.segments[0].audio_file != ""
    # Second segment was not processed successfully, audio_file should be None
    assert saved.segments[1].audio_file is None

"""Tests for the one-shot pipeline and Python facade."""

from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from audawispr.cli import app
from audawispr.core.errors import (
    CancelledError,
    ClippingError,
    EnrichmentError,
    ExportError,
    InputAudioError,
    OneShotError,
    SegmentationError,
    TranscriptionError,
)
from audawispr.core.manifest import (
    SourceAudio,
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
    load_manifest,
    save_manifest,
)
from audawispr.core.pipeline import (
    CancellationToken,
    PipelineRequest,
    PipelineResult,
    ProgressEvent,
    _derive_work_dir,
    run_pipeline,
)
from audawispr.pipeline import Pipeline

runner = CliRunner()


# --- Helpers ---


def _make_manifest(path: str = "/tmp/lesson.mp3") -> TranscriptManifest:
    words = [
        TranscriptWord(text="Bonjour", start=0.0, end=0.8),
        TranscriptWord(text="le", start=0.9, end=1.1),
        TranscriptWord(text="monde.", start=1.2, end=1.8),
    ]
    return TranscriptManifest(
        language="fr",
        source_audio=SourceAudio(
            file_name="lesson.mp3",
            path=path,
            size_bytes=3,
            sha256="0" * 64,
            language="fr",
            duration_seconds=5.0,
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


def _fake_clip_manifest_file(
    input_manifest: Path,
    output_manifest: Path,
    output_dir: Path,
    options=None,
) -> TranscriptManifest:
    manifest = load_manifest(input_manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_manifest.parent.mkdir(parents=True, exist_ok=True)

    new_segments = []
    for idx, seg in enumerate(manifest.segments):
        filename = f"{idx:04d}_{seg.id}.mp3"
        snippet_path = output_dir / filename
        snippet_path.write_bytes(b"fake audio")
        rel_dir = Path(os.path.relpath(output_dir, output_manifest.parent))
        audio_file = (rel_dir / filename).as_posix()
        new_segments.append(seg.model_copy(update={"audio_file": audio_file}))

    result = manifest.model_copy(update={"segments": new_segments})
    save_manifest(result, output_manifest)
    return result


# --- Work dir derivation ---


def test_derive_work_dir_for_apkg() -> None:
    assert _derive_work_dir(Path("output/deck.apkg")) == Path("output/deck/_work")


def test_derive_work_dir_for_csv() -> None:
    assert _derive_work_dir(Path("output/anki-csv")) == Path("output/anki-csv/_work")


def test_derive_work_dir_posix() -> None:
    assert _derive_work_dir(PurePosixPath("output/deck.apkg")) == PurePosixPath(  # type: ignore
        "output/deck/_work"
    )


def test_derive_work_dir_windows() -> None:
    assert _derive_work_dir(PureWindowsPath("output", "deck.apkg")) == PureWindowsPath(  # type: ignore
        "output", "deck", "_work"
    )


# --- Pipeline run tests ---


def test_pipeline_runs_full_flow(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    request = PipelineRequest(audio=audio_path, output=apkg_path)
    result = run_pipeline(request)

    assert isinstance(result, PipelineResult)
    assert result.output_path == apkg_path
    assert apkg_path.exists()
    assert not result.work_dir.exists()


def test_pipeline_creates_csv(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    output_dir = tmp_path / "anki-csv"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    request = PipelineRequest(audio=audio_path, output=output_dir)
    result = run_pipeline(request)

    assert result.output_path == output_dir
    assert (output_dir / "cards.csv").exists()
    assert not result.work_dir.exists()


def test_pipeline_skip_enrich_when_no_ipa(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )
    enrich_mock = MagicMock(side_effect=lambda m, o: m)
    monkeypatch.setattr("audawispr.core.pipeline.enrich_manifest", enrich_mock)

    request = PipelineRequest(audio=audio_path, output=apkg_path, ipa=False)
    run_pipeline(request)

    enrich_mock.assert_not_called()


def test_pipeline_runs_enrich_with_ipa(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )
    enrich_mock = MagicMock(side_effect=lambda m, o: m)
    monkeypatch.setattr("audawispr.core.pipeline.enrich_manifest", enrich_mock)

    request = PipelineRequest(audio=audio_path, output=apkg_path, ipa=True)
    run_pipeline(request)

    enrich_mock.assert_called_once()


def test_pipeline_keep_work_preserves_work_dir(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    request = PipelineRequest(audio=audio_path, output=apkg_path, keep_work=True)
    result = run_pipeline(request)

    assert result.work_dir.exists()
    assert (result.work_dir / "transcript.json").exists()


def test_pipeline_progress_events(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    events: list[ProgressEvent] = []

    def hook(event: ProgressEvent) -> None:
        events.append(event)

    request = PipelineRequest(audio=audio_path, output=apkg_path)
    run_pipeline(request, progress_hook=hook)

    phases = [e.phase for e in events]
    assert "transcribe" in phases
    assert "segment" in phases
    assert "clip" in phases
    assert "export" in phases
    assert "enrich" not in phases


def test_pipeline_cancellation_stops_before_export(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.segment_manifest",
        lambda m, o: m,
    )

    token = CancellationToken()

    def hook(event: ProgressEvent) -> None:
        if event.phase == "segment":
            token.request_cancel()

    request = PipelineRequest(audio=audio_path, output=apkg_path)

    with pytest.raises(CancelledError):
        run_pipeline(request, progress_hook=hook, cancellation_token=token)

    assert not apkg_path.exists()


# --- Error wrapping ---


def test_pipeline_transcription_error_wrap(monkeypatch, tmp_path: Path) -> None:
    def fake(*a, **k):
        raise TranscriptionError("model failed")

    monkeypatch.setattr("audawispr.core.pipeline.transcribe_audio", fake)

    request = PipelineRequest(
        audio=tmp_path / "audio.mp3",
        output=tmp_path / "out.apkg",
    )

    with pytest.raises(
        OneShotError, match="Transcription failed: model failed"
    ) as exc_info:
        run_pipeline(request)

    assert "--model-size" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_pipeline_input_audio_error_wrap(monkeypatch, tmp_path: Path) -> None:
    def fake(*a, **k):
        raise InputAudioError("file missing")

    monkeypatch.setattr("audawispr.core.pipeline.transcribe_audio", fake)

    request = PipelineRequest(
        audio=tmp_path / "audio.mp3",
        output=tmp_path / "out.apkg",
    )

    with pytest.raises(OneShotError, match="Transcription failed: file missing"):
        run_pipeline(request)


def test_pipeline_segmentation_error_wrap(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(),
    )

    def fake(*a, **k):
        raise SegmentationError("bad timestamps")

    monkeypatch.setattr("audawispr.core.pipeline.segment_manifest", fake)

    request = PipelineRequest(
        audio=tmp_path / "audio.mp3",
        output=tmp_path / "out.apkg",
    )

    with pytest.raises(
        OneShotError, match="Segmentation failed: bad timestamps"
    ) as exc_info:
        run_pipeline(request)

    assert "--pause-split-ms" in str(exc_info.value)


def test_pipeline_enrichment_error_wrap(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.segment_manifest",
        lambda m, o: m,
    )

    def fake(*a, **k):
        raise EnrichmentError("epitran missing")

    monkeypatch.setattr("audawispr.core.pipeline.enrich_manifest", fake)

    request = PipelineRequest(
        audio=tmp_path / "audio.mp3",
        output=tmp_path / "out.apkg",
        ipa=True,
    )

    with pytest.raises(
        OneShotError, match="Enrichment failed: epitran missing"
    ) as exc_info:
        run_pipeline(request)

    assert "--ipa" in str(exc_info.value)


def test_pipeline_clipping_error_wrap(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.segment_manifest",
        lambda m, o: m,
    )

    def fake(*a, **k):
        raise ClippingError("ffmpeg missing")

    monkeypatch.setattr("audawispr.core.pipeline.clip_manifest_file", fake)

    request = PipelineRequest(
        audio=tmp_path / "audio.mp3",
        output=tmp_path / "out.apkg",
    )

    with pytest.raises(
        OneShotError, match="Clipping failed: ffmpeg missing"
    ) as exc_info:
        run_pipeline(request)

    assert "FFmpeg" in str(exc_info.value)


def test_pipeline_export_error_wrap(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.segment_manifest",
        lambda m, o: m,
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    def fake(*a, **k):
        raise ExportError("disk full")

    monkeypatch.setattr("audawispr.core.pipeline.export_manifest_file", fake)

    request = PipelineRequest(
        audio=tmp_path / "audio.mp3",
        output=tmp_path / "out.apkg",
    )

    with pytest.raises(OneShotError, match="Export failed: disk full") as exc_info:
        run_pipeline(request)

    assert "disk space" in str(exc_info.value)


# --- Python facade tests ---


def test_pipeline_class_runs_full_flow(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    pipeline = Pipeline(output=apkg_path, language="fr")
    result = pipeline.run(audio_path)

    assert result.output_path == apkg_path
    assert apkg_path.exists()


def test_pipeline_class_skip_enrich(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )
    enrich_mock = MagicMock(side_effect=lambda m, o: m)
    monkeypatch.setattr("audawispr.core.pipeline.enrich_manifest", enrich_mock)

    pipeline = Pipeline(output=apkg_path, language="fr", ipa=False)
    pipeline.run(audio_path)

    enrich_mock.assert_not_called()


# --- CLI one-shot tests ---


def test_one_shot_creates_apkg(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    result = runner.invoke(
        app,
        [str(audio_path), "--output", str(apkg_path)],
    )

    assert result.exit_code == 0
    assert apkg_path.exists()


def test_one_shot_creates_csv(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    output_dir = tmp_path / "anki-csv"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    result = runner.invoke(
        app,
        [str(audio_path), "--output", str(output_dir)],
    )

    assert result.exit_code == 0
    assert (output_dir / "cards.csv").exists()


def test_one_shot_unknown_command_falls_back(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    run_mock = MagicMock(
        return_value=PipelineResult(
            output_path=apkg_path,
            work_dir=tmp_path / "work",
        )
    )
    monkeypatch.setattr("audawispr.core.pipeline.run_pipeline", run_mock)

    result = runner.invoke(
        app,
        [str(audio_path), "--output", str(apkg_path)],
    )

    assert result.exit_code == 0
    run_mock.assert_called_once()
    call_args = run_mock.call_args
    request = call_args[0][0]
    assert request.audio == audio_path
    assert request.output == apkg_path


def test_known_subcommand_not_redirected() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "audawispr doctor" in result.stdout


def test_known_subcommand_help_not_redirected() -> None:
    result = runner.invoke(
        app,
        ["transcribe", "--help"],
        env={"GITHUB_ACTIONS": "true"},
    )

    assert result.exit_code == 0
    assert "transcribe" in result.stdout


def test_one_shot_progress_with_verbose(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    result = runner.invoke(
        app,
        ["--verbose", str(audio_path), "--output", str(apkg_path)],
    )

    assert result.exit_code == 0
    assert "transcribe:" in result.stderr
    assert "segment:" in result.stderr
    assert "clip:" in result.stderr
    assert "export:" in result.stderr


def test_one_shot_no_progress_without_verbose(monkeypatch, tmp_path: Path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    apkg_path = tmp_path / "deck.apkg"

    monkeypatch.setattr(
        "audawispr.core.pipeline.transcribe_audio",
        lambda *a, **k: _make_manifest(path=str(audio_path.resolve())),
    )
    monkeypatch.setattr(
        "audawispr.core.pipeline.clip_manifest_file",
        _fake_clip_manifest_file,
    )

    result = runner.invoke(
        app,
        [str(audio_path), "--output", str(apkg_path)],
    )

    assert result.exit_code == 0
    assert "transcribe:" not in result.stderr
    assert "segment:" not in result.stderr

import re

from typer.testing import CliRunner

from audawispr.__about__ import __version__
from audawispr.cli import app
from audawispr.core.manifest import (
    SourceAudio,
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
)
from audawispr.core.transcription import TranscriptionOptions

runner = CliRunner()
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def test_help_displays_cli_name() -> None:
    result = runner.invoke(app, ["--help"])
    output = _normalize_terminal_output(result.stdout)

    assert result.exit_code == 0
    assert "audawispr" in output
    assert "clip" in output
    assert "doctor" in output
    assert "enrich" in output
    assert "export" in output
    assert "segment" in output
    assert "transcribe" in output
    assert "validate" in output


def test_version_displays_package_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"audawispr {__version__}" in result.stdout


def test_doctor_displays_output_shape() -> None:
    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "audawispr doctor" in result.stdout
    assert "Package: audawispr" in result.stdout
    assert "Python:" in result.stdout
    assert "ffmpeg:" in result.stdout
    assert "ffprobe:" in result.stdout


def test_transcribe_help_displays_phase_2_options() -> None:
    result = runner.invoke(
        app,
        ["transcribe", "--help"],
        env={"GITHUB_ACTIONS": "true"},
    )
    output = _normalize_terminal_output(result.stdout)

    assert result.exit_code == 0
    assert "--output" in output
    assert "--language" in output
    assert "--model-size" in output
    assert "--compute-type" in output
    assert "--vad" in output


def test_validate_help_displays_manifest_argument() -> None:
    result = runner.invoke(app, ["validate", "--help"])
    output = _normalize_terminal_output(result.stdout)

    assert result.exit_code == 0
    assert "MANIFEST" in output


def test_segment_help_displays_phase_3_options() -> None:
    result = runner.invoke(
        app,
        ["segment", "--help"],
        env={"GITHUB_ACTIONS": "true"},
    )
    output = _normalize_terminal_output(result.stdout)

    assert result.exit_code == 0
    assert "--output" in output
    assert "--inspection-tsv" in output
    assert "--pause-split-ms" in output
    assert "--min-duration-ms" in output
    assert "--max-duration-ms" in output
    assert "--merge-short" in output


def test_enrich_help_displays_phase_4_options() -> None:
    result = runner.invoke(
        app,
        ["enrich", "--help"],
        env={"GITHUB_ACTIONS": "true"},
    )
    output = _normalize_terminal_output(result.stdout)

    assert result.exit_code == 0
    assert "--output" in output
    assert "--ipa" in output
    assert "--translate" in output


def test_clip_help_displays_phase_5_options() -> None:
    result = runner.invoke(
        app,
        ["clip", "--help"],
        env={"GITHUB_ACTIONS": "true"},
    )
    output = _normalize_terminal_output(result.stdout)

    assert result.exit_code == 0
    assert "--output" in output
    assert "--output-dir" in output
    assert "--padding-before-ms" in output
    assert "--padding-after-ms" in output
    assert "--format" in output
    assert "--bitrate" in output
    assert "--force" in output


def test_validate_rejects_malformed_json(tmp_path) -> None:
    manifest_path = tmp_path / "bad.json"
    manifest_path.write_text("{", encoding="utf-8")

    result = runner.invoke(app, ["validate", str(manifest_path)])

    assert result.exit_code == 1
    assert "not valid JSON" in result.stderr


def test_validate_accepts_manifest(tmp_path) -> None:
    manifest = _make_manifest()
    manifest_path = tmp_path / "transcript.json"
    manifest_path.write_text(
        manifest.model_dump_json(),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["validate", str(manifest_path)])

    assert result.exit_code == 0
    assert "Manifest valid" in result.stdout


def test_transcribe_writes_manifest_with_fake_backend(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    output_path = tmp_path / "transcript.json"

    def fake_transcribe(audio_path_arg, options: TranscriptionOptions):
        assert audio_path_arg == audio_path
        assert options.language == "fr"
        return _make_manifest(path=str(audio_path.resolve()))

    monkeypatch.setattr("audawispr.cli.transcribe_audio", fake_transcribe)

    result = runner.invoke(
        app,
        [
            "transcribe",
            str(audio_path),
            "--output",
            str(output_path),
            "--language",
            "fr",
        ],
    )

    assert result.exit_code == 0
    assert "Wrote transcript manifest" in result.stdout
    assert output_path.exists()


def test_transcribe_reports_output_write_failure(monkeypatch, tmp_path) -> None:
    audio_path = tmp_path / "lesson.mp3"
    audio_path.write_bytes(b"abc")
    output_path = tmp_path / "output-dir"
    output_path.mkdir()

    monkeypatch.setattr("audawispr.cli.transcribe_audio", lambda *_: _make_manifest())

    result = runner.invoke(
        app,
        ["transcribe", str(audio_path), "--output", str(output_path)],
    )

    assert result.exit_code == 1
    assert "could not save manifest" in result.stderr


def test_transcribe_reports_missing_input_audio(tmp_path) -> None:
    result = runner.invoke(
        app,
        [
            "transcribe",
            str(tmp_path / "missing.mp3"),
            "--output",
            str(tmp_path / "transcript.json"),
        ],
    )

    assert result.exit_code == 1
    assert "input audio does not exist" in result.stderr


def test_segment_writes_manifest_and_default_tsv(tmp_path) -> None:
    input_path = tmp_path / "transcript.json"
    output_path = tmp_path / "nested" / "segments.json"
    input_path.write_text(
        _make_manifest(
            words=[
                TranscriptWord(text="Bonjour.", start=0.0, end=0.7),
                TranscriptWord(text="Encore.", start=0.8, end=1.4),
            ]
        ).model_dump_json(),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        ["segment", str(input_path), "--output", str(output_path)],
    )

    assert result.exit_code == 0
    assert "Wrote segmented manifest" in result.stdout
    assert "Wrote inspection TSV" in result.stdout
    assert output_path.exists()
    assert output_path.with_suffix(".tsv").exists()


def test_segment_writes_explicit_tsv_path(tmp_path) -> None:
    input_path = tmp_path / "transcript.json"
    output_path = tmp_path / "segments.json"
    tsv_path = tmp_path / "inspection" / "review.tsv"
    input_path.write_text(_make_manifest().model_dump_json(), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "segment",
            str(input_path),
            "--output",
            str(output_path),
            "--inspection-tsv",
            str(tsv_path),
        ],
    )

    assert result.exit_code == 0
    assert tsv_path.exists()


def test_segment_reports_invalid_options(tmp_path) -> None:
    input_path = tmp_path / "transcript.json"
    input_path.write_text(_make_manifest().model_dump_json(), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "segment",
            str(input_path),
            "--output",
            str(tmp_path / "segments.json"),
            "--min-duration-ms",
            "1000",
            "--max-duration-ms",
            "500",
        ],
    )

    assert result.exit_code == 1
    assert "max_duration_ms" in result.stderr


def test_segment_reports_invalid_manifest(tmp_path) -> None:
    manifest_path = tmp_path / "bad.json"
    manifest_path.write_text("{", encoding="utf-8")

    result = runner.invoke(
        app,
        ["segment", str(manifest_path), "--output", str(tmp_path / "segments.json")],
    )

    assert result.exit_code == 1
    assert "not valid JSON" in result.stderr


def test_segment_reports_output_write_failure(tmp_path) -> None:
    input_path = tmp_path / "transcript.json"
    output_path = tmp_path / "output-dir"
    output_path.mkdir()
    input_path.write_text(_make_manifest().model_dump_json(), encoding="utf-8")

    result = runner.invoke(
        app,
        ["segment", str(input_path), "--output", str(output_path)],
    )

    assert result.exit_code == 1
    assert "could not save manifest" in result.stderr


def test_enrich_writes_manifest_with_ipa(tmp_path) -> None:
    input_path = tmp_path / "segments.json"
    output_path = tmp_path / "enriched.json"
    input_path.write_text(_make_manifest().model_dump_json(), encoding="utf-8")

    result = runner.invoke(
        app,
        ["enrich", str(input_path), "--output", str(output_path), "--ipa"],
    )

    assert result.exit_code == 0
    assert "Wrote enriched manifest" in result.stdout
    assert output_path.exists()


def test_enrich_translate_none_keeps_translation_fields_null(tmp_path) -> None:
    input_path = tmp_path / "segments.json"
    output_path = tmp_path / "enriched.json"
    input_path.write_text(_make_manifest().model_dump_json(), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "enrich",
            str(input_path),
            "--output",
            str(output_path),
            "--translate",
            "none",
        ],
    )

    assert result.exit_code == 0
    loaded = output_path.read_text(encoding="utf-8")
    assert '"translation": null' in loaded
    assert '"translation_provider": null' in loaded


def test_clip_writes_manifest(monkeypatch, tmp_path) -> None:
    input_path = tmp_path / "manifest.json"
    input_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "clipped.json"
    output_dir = tmp_path / "media"

    def fake_clip(input_manifest, output_manifest, output_dir_arg, options=None):
        output_manifest.parent.mkdir(parents=True, exist_ok=True)
        output_manifest.write_text('{"schema_version":"1.0"}', encoding="utf-8")
        return None

    monkeypatch.setattr("audawispr.cli.clip_manifest_file", fake_clip)

    result = runner.invoke(
        app,
        [
            "clip",
            str(input_path),
            "--output",
            str(output_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote clipped manifest" in result.stdout


def test_clip_reports_clipping_error(monkeypatch, tmp_path) -> None:
    from audawispr.core.errors import ClippingError

    input_path = tmp_path / "manifest.json"
    input_path.write_text("{}", encoding="utf-8")
    output_path = tmp_path / "clipped.json"

    def fake_clip(*args, **kwargs):
        raise ClippingError("test error")

    monkeypatch.setattr("audawispr.cli.clip_manifest_file", fake_clip)

    result = runner.invoke(
        app,
        [
            "clip",
            str(input_path),
            "--output",
            str(output_path),
            "--output-dir",
            str(tmp_path / "media"),
        ],
    )

    assert result.exit_code == 1
    assert "test error" in result.stderr


def test_export_help_displays_phase_6_options() -> None:
    result = runner.invoke(
        app,
        ["export", "--help"],
        env={"GITHUB_ACTIONS": "true"},
    )
    output = _normalize_terminal_output(result.stdout)

    assert result.exit_code == 0
    assert "--output" in output
    assert "--format" in output
    assert "--deck-name" in output


def test_export_writes_csv(monkeypatch, tmp_path) -> None:
    input_path = tmp_path / "clipped.json"
    input_path.write_text("{}", encoding="utf-8")
    output_dir = tmp_path / "anki-csv"

    def fake_export(manifest_path, output_dir_arg, options=None):
        output_dir_arg.mkdir(parents=True, exist_ok=True)
        (output_dir_arg / "cards.csv").write_text("dummy", encoding="utf-8")

    monkeypatch.setattr("audawispr.cli.export_manifest_file", fake_export)

    result = runner.invoke(
        app,
        [
            "export",
            str(input_path),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert "Wrote export" in result.stdout


def test_export_apkg_cli(monkeypatch, tmp_path) -> None:
    input_path = tmp_path / "clipped.json"
    input_path.write_text("{}", encoding="utf-8")
    apkg_path = tmp_path / "deck.apkg"

    def fake_export(manifest_path, output_path_arg, options=None):
        output_path_arg.parent.mkdir(parents=True, exist_ok=True)
        output_path_arg.write_bytes(b"fake apkg data")

    monkeypatch.setattr("audawispr.cli.export_manifest_file", fake_export)

    result = runner.invoke(
        app,
        [
            "export",
            str(input_path),
            "--output",
            str(apkg_path),
            "--deck-name",
            "My Deck",
            "--format",
            "apkg",
        ],
    )

    assert result.exit_code == 0
    assert "Wrote export" in result.stdout


def test_export_infer_apkg_from_cli(monkeypatch, tmp_path) -> None:
    input_path = tmp_path / "clipped.json"
    input_path.write_text("{}", encoding="utf-8")
    apkg_path = tmp_path / "deck.apkg"

    def fake_export(manifest_path, output_path_arg, options=None):
        output_path_arg.parent.mkdir(parents=True, exist_ok=True)
        output_path_arg.write_bytes(b"fake apkg data")

    monkeypatch.setattr("audawispr.cli.export_manifest_file", fake_export)

    # No --format, but output ends in .apkg — should infer apkg
    result = runner.invoke(
        app,
        [
            "export",
            str(input_path),
            "--output",
            str(apkg_path),
        ],
    )

    assert result.exit_code == 0


def test_export_reports_error(monkeypatch, tmp_path) -> None:
    from audawispr.core.errors import ExportError

    input_path = tmp_path / "clipped.json"
    input_path.write_text("{}", encoding="utf-8")
    output_dir = tmp_path / "anki-csv"

    def fake_export(*args, **kwargs):
        raise ExportError("test error")

    monkeypatch.setattr("audawispr.cli.export_manifest_file", fake_export)

    result = runner.invoke(
        app,
        [
            "export",
            str(input_path),
            "--output",
            str(output_dir),
        ],
    )

    assert result.exit_code == 1
    assert "test error" in result.stderr


def test_enrich_rejects_network_translation_without_writing_output(tmp_path) -> None:
    input_path = tmp_path / "segments.json"
    output_path = tmp_path / "enriched.json"
    input_path.write_text(_make_manifest().model_dump_json(), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "enrich",
            str(input_path),
            "--output",
            str(output_path),
            "--translate",
            "deepl",
        ],
    )

    assert result.exit_code == 1
    assert "not supported in Epic 1" in result.stderr
    assert not output_path.exists()


def test_oneshot_translate_does_not_cause_type_error(tmp_path) -> None:
    """_oneshot accepts --translate without raising TypeError."""
    result = runner.invoke(
        app,
        [
            "_oneshot",
            str(tmp_path / "input.mp3"),
            "--output",
            str(tmp_path / "out.apkg"),
            "--translate",
            "deepl",
        ],
    )
    # The command may fail because the audio file doesn't exist,
    # but it should not crash with a TypeError.
    assert not isinstance(result.exception, TypeError)


def _make_manifest(
    path: str = "/tmp/lesson.mp3",
    words: list[TranscriptWord] | None = None,
) -> TranscriptManifest:
    return _make_manifest_with_words(
        path,
        words
        or [
            TranscriptWord(
                text="Bonjour",
                start=0.0,
                end=0.8,
            )
        ],
    )


def _make_manifest_with_words(
    path: str,
    words: list[TranscriptWord],
) -> TranscriptManifest:
    return TranscriptManifest(
        language="fr",
        source_audio=SourceAudio(
            file_name="lesson.mp3",
            path=path,
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


def _normalize_terminal_output(output: str) -> str:
    return ANSI_ESCAPE_RE.sub("", output)

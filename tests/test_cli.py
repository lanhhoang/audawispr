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
    assert "doctor" in output
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


def _make_manifest(path: str = "/tmp/lesson.mp3") -> TranscriptManifest:
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
        ],
    )


def _normalize_terminal_output(output: str) -> str:
    return ANSI_ESCAPE_RE.sub("", output)

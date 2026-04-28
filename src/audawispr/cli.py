"""Command line interface for audawispr."""

from pathlib import Path
from typing import Annotated

import typer

from audawispr.__about__ import __version__
from audawispr.core.diagnostics import collect_diagnostics
from audawispr.core.errors import AudawisprError
from audawispr.core.manifest import load_manifest, save_manifest
from audawispr.core.transcription import TranscriptionOptions, transcribe_audio

app = typer.Typer(
    add_completion=False,
    help="Turn language-learning audio into Anki-ready study materials.",
    no_args_is_help=True,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"audawispr {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_version_callback,
            help="Show the audawispr version and exit.",
            is_eager=True,
        ),
    ] = False,
) -> None:
    """Turn language-learning audio into Anki-ready study materials."""


@app.command()
def doctor() -> None:
    """Report local runtime readiness."""
    report = collect_diagnostics()

    typer.echo("audawispr doctor")
    typer.echo(f"Package: audawispr {report.package_version}")
    typer.echo(f"Python: {report.python_version}")

    for tool in report.tools:
        status = "ok" if tool.available else "missing"
        typer.echo(f"{tool.name}: {status} ({tool.source})")
        if tool.path is not None:
            typer.echo(f"  path: {tool.path}")
        if tool.version:
            typer.echo(f"  version: {tool.version}")
        if tool.message:
            typer.echo(f"  note: {tool.message}")


@app.command()
def validate(
    manifest: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Transcript manifest JSON to validate.",
        ),
    ],
) -> None:
    """Validate a transcript manifest schema and timestamps."""
    try:
        load_manifest(manifest)
    except AudawisprError as exc:
        _fail(str(exc))

    typer.echo(f"Manifest valid: {manifest}")


@app.command()
def transcribe(
    audio: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Source audio file to transcribe.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Transcript manifest JSON output path.",
        ),
    ],
    language: Annotated[
        str,
        typer.Option("--language", "-l", help="Source language code."),
    ] = "fr",
    model_size: Annotated[
        str,
        typer.Option("--model-size", help="faster-whisper model size or path."),
    ] = "small",
    device: Annotated[
        str,
        typer.Option("--device", help="faster-whisper device."),
    ] = "auto",
    compute_type: Annotated[
        str,
        typer.Option("--compute-type", help="faster-whisper compute type."),
    ] = "int8",
    vad: Annotated[
        bool,
        typer.Option("--vad/--no-vad", help="Enable faster-whisper VAD filtering."),
    ] = True,
) -> None:
    """Transcribe audio locally into a transcript manifest."""
    options = TranscriptionOptions(
        language=language,
        model_size=model_size,
        device=device,
        compute_type=compute_type,
        vad=vad,
    )

    try:
        manifest = transcribe_audio(audio, options)
        save_manifest(manifest, output)
        load_manifest(output)
    except AudawisprError as exc:
        _fail(str(exc))

    typer.echo(f"Wrote transcript manifest: {output}")


def _fail(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)

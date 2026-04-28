"""Command line interface for audawispr."""

from pathlib import Path
from typing import Annotated

import typer

from audawispr.__about__ import __version__
from audawispr.core.clipping import ClipOptions, clip_manifest_file
from audawispr.core.diagnostics import collect_diagnostics
from audawispr.core.enrichment import EnrichmentOptions, enrich_manifest_file
from audawispr.core.errors import AudawisprError, ClippingError, ExportError
from audawispr.core.export import ExportOptions, export_manifest_file
from audawispr.core.manifest import load_manifest, save_manifest
from audawispr.core.segmentation import (
    SegmentationOptions,
    default_inspection_tsv_path,
    save_inspection_tsv,
    segment_manifest,
)
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


@app.command()
def segment(
    manifest: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Transcript manifest JSON to segment.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Segmented manifest JSON output path.",
        ),
    ],
    inspection_tsv: Annotated[
        Path | None,
        typer.Option(
            "--inspection-tsv",
            help="Inspection TSV output path. Defaults next to the JSON output.",
        ),
    ] = None,
    pause_split_ms: Annotated[
        int,
        typer.Option("--pause-split-ms", help="Pause threshold for splitting."),
    ] = 700,
    min_duration_ms: Annotated[
        int,
        typer.Option("--min-duration-ms", help="Minimum segment duration."),
    ] = 600,
    max_duration_ms: Annotated[
        int,
        typer.Option("--max-duration-ms", help="Maximum segment duration."),
    ] = 7000,
    merge_short: Annotated[
        bool,
        typer.Option(
            "--merge-short/--no-merge-short",
            help="Merge segments shorter than the minimum duration.",
        ),
    ] = True,
) -> None:
    """Segment a transcript manifest into sentence-like learning units."""
    try:
        options = SegmentationOptions(
            pause_split_ms=pause_split_ms,
            min_duration_ms=min_duration_ms,
            max_duration_ms=max_duration_ms,
            merge_short=merge_short,
        )
        transcript = load_manifest(manifest)
        segmented_manifest = segment_manifest(transcript, options)
        save_manifest(segmented_manifest, output)
        load_manifest(output)

        tsv_output = (
            default_inspection_tsv_path(output)
            if inspection_tsv is None
            else inspection_tsv
        )
        save_inspection_tsv(segmented_manifest, tsv_output)
    except AudawisprError as exc:
        _fail(str(exc))

    typer.echo(f"Wrote segmented manifest: {output}")
    typer.echo(f"Wrote inspection TSV: {tsv_output}")


@app.command()
def enrich(
    manifest: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Segmented manifest JSON to enrich.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Enriched manifest JSON output path.",
        ),
    ],
    ipa: Annotated[
        bool,
        typer.Option("--ipa/--no-ipa", help="Generate IPA pronunciation."),
    ] = False,
    translate: Annotated[
        str,
        typer.Option(
            "--translate",
            help="Translation provider. Epic 1 supports only 'none'.",
        ),
    ] = "none",
) -> None:
    """Add optional IPA and translation fields to a segmented manifest."""
    try:
        options = EnrichmentOptions(
            ipa=ipa,
            translation_provider=translate,
        )
        enrich_manifest_file(manifest, output, options)
    except AudawisprError as exc:
        _fail(str(exc))

    typer.echo(f"Wrote enriched manifest: {output}")


@app.command()
def clip(
    manifest: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Segmented or enriched manifest JSON to clip.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Clipped manifest JSON output path.",
        ),
    ],
    output_dir: Annotated[
        Path,
        typer.Option(
            "--output-dir",
            help="Directory for generated audio snippets.",
        ),
    ],
    padding_before_ms: Annotated[
        int,
        typer.Option(
            "--padding-before-ms",
            help="Padding before each segment in milliseconds.",
        ),
    ] = 150,
    padding_after_ms: Annotated[
        int,
        typer.Option(
            "--padding-after-ms",
            help="Padding after each segment in milliseconds.",
        ),
    ] = 250,
    audio_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Output audio format.",
        ),
    ] = "mp3",
    bitrate: Annotated[
        str,
        typer.Option(
            "--bitrate",
            help="Output audio bitrate.",
        ),
    ] = "128k",
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Re-clip even if snippet already exists.",
        ),
    ] = False,
) -> None:
    """Clip audio snippets from a segmented or enriched manifest."""
    try:
        options = ClipOptions(
            padding_before_ms=padding_before_ms,
            padding_after_ms=padding_after_ms,
            audio_format=audio_format,
            bitrate=bitrate,
            force=force,
        )
        clip_manifest_file(manifest, output, output_dir, options)
    except ClippingError as exc:
        _fail(str(exc))

    typer.echo(f"Wrote clipped manifest: {output}")


@app.command()
def export(
    manifest: Annotated[
        Path,
        typer.Argument(
            exists=False,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Clipped manifest JSON to export.",
        ),
    ],
    output: Annotated[
        Path,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for CSV and media.",
        ),
    ],
    format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Export format. Epic 1 supports only 'anki-csv'.",
        ),
    ] = "anki-csv",
) -> None:
    """Export a clipped manifest to Anki-compatible format."""
    try:
        options = ExportOptions(format=format)
        export_manifest_file(manifest, output, options)
    except ExportError as exc:
        _fail(str(exc))

    typer.echo(f"Wrote export: {output}")


def _fail(message: str) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(1)

"""Command line interface for audawispr."""

from typing import Annotated

import typer

from audawispr.__about__ import __version__
from audawispr.core.diagnostics import collect_diagnostics

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

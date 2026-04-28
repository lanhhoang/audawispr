# Phase 1: Project Foundation + Diagnostics

## Goal

Deliver a runnable Python package with a Typer CLI, reusable package structure,
development tooling, and diagnostics. After this phase, users can verify the app
is installed and inspect local runtime readiness.

## User-Usable Result

- `uv run audawispr --help` displays the CLI.
- `uv run audawispr --version` displays the package version.
- `uv run audawispr doctor` reports Python/package readiness and FFmpeg/FFprobe
  availability.

## TODO

- [ ] Scaffold `pyproject.toml` with `hatchling`, `uv`, Python 3.11+,
  `typer`, `static-ffmpeg`, `pytest`, `ruff`, and `ty`.
- [ ] Add package skeleton under `src/audawispr/` with `__init__.py`,
  `__about__.py`, `__main__.py`, and `cli.py`.
- [ ] Add `.gitignore` entries for `.venv/`, Python caches, tool caches,
  Whisper/model caches, generated manifests, snippets, decks, and output
  directories.
- [ ] Add a Typer app with `--version`, `doctor`, and placeholder subcommand
  registration points for later phases.
- [ ] Add a small diagnostics core that checks Python version, package version,
  and FFmpeg/FFprobe availability from environment variables, `PATH`, or
  static-ffmpeg.
- [ ] Add initial tests for CLI help, version output, and doctor output shape.
- [ ] Update README with installation and Phase 1 diagnostics usage.

## Acceptance Checks

- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr --help`
- [ ] `uv run audawispr --version`
- [ ] `uv run audawispr doctor`

## Notes

- Do not implement transcription or manifest behavior in this phase.
- Keep diagnostics useful even when FFmpeg is missing; missing tools should be
  reported, not crash the command.
- Do not commit generated transcription output, snippets, APKG files, model
  caches, or machine-specific paths.

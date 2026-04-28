# audawispr

Split audio files into high-quality sentence-based learning materials.

## Status

This repository is implementing Epic 1: a Python CLI and reusable core library
for turning language-learning audio into Anki-ready study materials.

Phase 1 provides the project scaffold, CLI entrypoint, development tooling, CI,
and local runtime diagnostics. Transcription, segmentation, audio clipping, and
Anki export are planned for later phases.

## Requirements

- Python 3.11+
- uv
- FFmpeg and FFprobe are optional for Phase 1 diagnostics, but will be required
  for later audio processing phases.

## Setup

Install runtime and development dependencies:

```sh
uv sync --dev
```

## Usage

Show the CLI help:

```sh
uv run audawispr --help
```

Show the installed package version:

```sh
uv run audawispr --version
```

Check local runtime readiness:

```sh
uv run audawispr doctor
```

`doctor` reports the audawispr package version, Python version, and whether
FFmpeg and FFprobe are available from `AUDAWISPR_FFMPEG`, `AUDAWISPR_FFPROBE`,
`PATH`, or the `static-ffmpeg` fallback.

## Development Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check src tests
```

## CI

GitHub Actions runs the same quality checks with `uv sync --dev --frozen`.
Because this is a private repository, the workflow keeps routine pushes cheaper:

- Ubuntu runs on pushes and pull requests targeting `master`.
- macOS and Windows run on pull requests targeting `master` and on manual
  `workflow_dispatch` runs.

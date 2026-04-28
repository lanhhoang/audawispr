# audawispr

Split audio files into high-quality sentence-based learning materials.

## Status

This repository is implementing Epic 1: a Python CLI and reusable core library
for turning language-learning audio into Anki-ready study materials.

Phase 2 provides local `faster-whisper` transcription into a validated JSON
manifest. Segmentation, audio clipping, and Anki export are planned for later
phases.

## Requirements

- Python 3.11+
- uv
- FFmpeg and FFprobe are optional for diagnostics and best-effort source audio
  duration metadata. Later audio processing phases will require them.

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

Transcribe audio locally into a transcript manifest:

```sh
uv run audawispr transcribe lesson.mp3 --output out/transcript.json --language fr
```

Validate an existing transcript manifest:

```sh
uv run audawispr validate out/transcript.json
```

`transcribe` defaults to French, the `small` faster-whisper model, automatic
device selection, `int8` compute, VAD enabled, and required word timestamps.
The first real transcription may download model files, but no transcription API
key is required. Normal tests and CI use fakes and do not download models.

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

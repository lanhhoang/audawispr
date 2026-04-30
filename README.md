# audawispr

[![Quality](https://github.com/lanhhoang/audawispr/actions/workflows/quality.yml/badge.svg)](https://github.com/lanhhoang/audawispr/actions/workflows/quality.yml)
[![PyPI version](https://img.shields.io/pypi/v/audawispr.svg)](https://pypi.org/project/audawispr/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Split audio files into high-quality sentence-based learning materials.

## Features

- **Transcription** — Local speech-to-text via `faster-whisper`; no API keys required.
- **Segmentation** — Splits transcriptions into sentence-level segments using punctuation, pauses, and duration bounds.
- **Enrichment** — French IPA transcription (optional). Translation scaffolding is in place but not yet implemented.
- **Clipping** — Extracts audio snippets for each segment using FFmpeg (bundled via `static-ffmpeg`).
- **Export** — Outputs Anki-compatible CSV or native `.apkg` packages with embedded audio.
- **One-shot CLI** — Runs the full pipeline with a single command.

## Requirements

- Python 3.11+
- FFmpeg is bundled via the `static-ffmpeg` dependency — no separate installation is needed. Run `audawispr doctor` to verify availability.
- `uv` is only required for local development (see Setup).

## Setup

Install audawispr from PyPI:

```sh
pip install audawispr
```

Or with uv:

```sh
uv pip install audawispr
```

After installing, run `audawispr` directly. Use `uv run audawispr` only when working in a cloned repository.

For local development, install runtime and development dependencies:

```sh
uv sync --dev
```

## Quickstart

Turn an audio file into an Anki deck with one command:

```sh
audawispr lesson.mp3 --output deck.apkg --language fr --ipa
```

Or use the Python API:

```python
from pathlib import Path
from audawispr import Pipeline

Pipeline(
    output=Path("deck.apkg"),
    language="fr",
    ipa=True,
).run(Path("lesson.mp3"))
```

The one-shot command runs transcription, segmentation, enrichment, clipping, and export in sequence.

## Usage

This section and Quickstart use the bare `audawispr` command. For development, prefix with `uv run`.

Show the CLI help:

```sh
audawispr --help
```

Show the installed package version:

```sh
audawispr --version
```

Check local runtime readiness:

```sh
audawispr doctor
```

`audawispr doctor` reports the package version, Python version, and whether FFmpeg and FFprobe are available from `AUDAWISPR_FFMPEG`, `AUDAWISPR_FFPROBE`, `PATH`, or the `static-ffmpeg` fallback.

Transcribe audio locally into a transcript manifest:

```sh
audawispr transcribe lesson.mp3 --output out/transcript.json --language fr
```

Validate an existing transcript manifest:

```sh
audawispr validate out/transcript.json
```

Segment a transcript manifest and write an inspection TSV:

```sh
audawispr segment out/transcript.json --output out/segments.json
```

Enrich a segmented French manifest with IPA:

```sh
audawispr enrich out/segments.json --ipa --output out/enriched.json
```

`transcribe` defaults to French, the `small` faster-whisper model, automatic device selection, `int8` compute, VAD enabled, and required word timestamps. The first real transcription may download model files, but no API key is required. Tests and CI use fakes and do not download models.

`segment` preserves the transcript manifest schema and rebuilds only the segment list. It splits on sentence punctuation, pauses, and duration bounds. By default, it writes `out/segments.tsv` next to the JSON output; use `--inspection-tsv path/to/review.tsv` to choose a different TSV path.

`enrich` preserves timestamps, words, and source metadata while adding optional study fields. IPA (`--ipa`) is available for French. Translation is not yet implemented; pass `--translate none` (the default) to skip it. The pipeline works with any language faster-whisper supports — IPA is the only French-specific feature.

Clip audio snippets from a segmented manifest:

```sh
audawispr clip out/enriched.json --output out/clipped.json --output-dir out/media
```

`clip` reads a segmented or enriched manifest, extracts each segment's audio from the source file using FFmpeg, and writes the clipped manifest with `audio_file` paths. By default it reuses existing snippets; use `--force` to re-clip. Padding (`--padding-before-ms`, `--padding-after-ms`), format (`--format`), and bitrate (`--bitrate`) are configurable.

Export a clipped manifest for Anki import:

```sh
audawispr export out/clipped.json --format anki-csv --output out/anki-csv
```

`export` reads a clipped manifest, copies audio snippets, and writes `out/anki-csv/cards.csv` with columns `SourceText`, `Audio`, `IPA`, `Translation`, `SourceFile`, `TimestampRange`, and `SegmentId`. Audio references use Anki's `[sound:...]` syntax.

Manual import in Anki Desktop: File → Import → select `cards.csv`, set "Fields separated by: Comma", and copy the `media/` folder contents into your Anki `collection.media` folder.

Export as a native Anki package (`.apkg`) with embedded audio:

```sh
audawispr export out/clipped.json --output deck.apkg --deck-name "My French Deck"
```

When the output path ends in `.apkg`, the `apkg` format is inferred automatically. Use `--deck-name` to set the deck name; the default is `audawispr::{language}` (e.g. `audawispr::fr`). The resulting `.apkg` file can be opened directly in Anki Desktop via File → Import.

## Development Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check src tests
```


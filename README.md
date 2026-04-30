# audawispr

[![Quality](https://github.com/lanhhoang/audawispr/actions/workflows/quality.yml/badge.svg)](https://github.com/lanhhoang/audawispr/actions/workflows/quality.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

Split audio files into high-quality sentence-based learning materials.

## Status

This repository is implementing Epic 1: a Python CLI and reusable core library
for turning language-learning audio into Anki-ready study materials.

Epic 1 is complete: local `faster-whisper` transcription, timestamp-aware
segmentation, French IPA enrichment, audio clipping, Anki CSV export, native
`.apkg` export, and a one-shot CLI are all implemented.

## Requirements

- Python 3.11+
- uv
- FFmpeg and FFprobe are optional for diagnostics and best-effort source audio
  duration metadata. Later audio processing phases will require them.

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

For local development:

Install runtime and development dependencies:

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
from audawispr.pipeline import Pipeline

Pipeline(
    output=Path("deck.apkg"),
    language="fr",
    ipa=True,
).run(Path("lesson.mp3"))
```

The one-shot command runs transcription, segmentation, enrichment, clipping, and
export in sequence. Intermediate files are stored in a work directory next to the
output (e.g. `deck/_work/` for `deck.apkg`, or `<output>/_work/` for CSV) and
cleaned up on success unless `--keep-work` is passed.

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

`doctor` reports the audawispr package version, Python version, and whether
FFmpeg and FFprobe are available from `AUDAWISPR_FFMPEG`, `AUDAWISPR_FFPROBE`,
`PATH`, or the `static-ffmpeg` fallback.

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

`transcribe` defaults to French, the `small` faster-whisper model, automatic
device selection, `int8` compute, VAD enabled, and required word timestamps.
The first real transcription may download model files, but no transcription API
key is required. Normal tests and CI use fakes and do not download models.

`segment` preserves the transcript manifest schema and rebuilds only the segment
list. It splits on sentence punctuation, pauses, and duration bounds. By
default, it writes `out/segments.tsv` next to the JSON output; use
`--inspection-tsv path/to/review.tsv` to choose a different TSV path.

`enrich` preserves timestamps, words, and source metadata while adding optional
study fields. IPA is opt-in with `--ipa` and is French-only in Epic 1.
Translation is stubbed: `--translate none` is the default and performs no
network access. Online providers such as `deepl` and `openai` are not
implemented in Epic 1.

Clip audio snippets from a segmented manifest:

```sh
audawispr clip out/enriched.json --output out/clipped.json --output-dir out/media
```

`clip` reads a segmented or enriched manifest, extracts each segment's audio
from the source file using FFmpeg, and writes the clipped manifest with
`audio_file` paths. By default it reuses existing snippets; use `--force` to
re-clip. Padding (`--padding-before-ms`, `--padding-after-ms`), format
(`--format`), and bitrate (`--bitrate`) are configurable.

Export a clipped manifest for Anki import:

```sh
audawispr export out/clipped.json --format anki-csv --output out/anki-csv
```

`export` reads a clipped manifest, copies audio snippets, and writes
`out/anki-csv/cards.csv` with columns `SourceText`, `Audio`, `IPA`,
`Translation`, `SourceFile`, `TimestampRange`, and `SegmentId`. Audio
references use Anki's `[sound:...]` syntax.

Manual import in Anki Desktop: File → Import → select `cards.csv`,
set "Fields separated by: Comma", and copy the `media/` folder contents
into your Anki collection.media folder.

Export as a native Anki package (`.apkg`) with embedded audio:

```sh
audawispr export out/clipped.json --output deck.apkg --deck-name "My French Deck"
```

When the output path ends in `.apkg`, the `apkg` format is inferred
automatically. Use `--deck-name` to set the deck name; the default is
`audawispr::{language}` (e.g. `audawispr::fr`). The resulting `.apkg` file can
be opened directly in Anki Desktop via File → Import.

## Development Checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check src tests
```

## CI

GitHub Actions runs the same quality checks with `uv sync --dev --frozen`.
The workflow keeps routine pushes cheaper:

- Ubuntu runs on pushes and pull requests targeting `master`.
- macOS and Windows run on pull requests targeting `master` and on manual
  `workflow_dispatch` runs.

# audawispr

Split audio files into high-quality sentence-based learning materials.

## Status

This repository is implementing Epic 1: a Python CLI and reusable core library
for turning language-learning audio into Anki-ready study materials.

Phase 4 provides local `faster-whisper` transcription into a validated JSON
manifest, timestamp-aware segmentation into sentence-like learning units, and
French IPA enrichment. Audio clipping, Anki CSV export, and native `.apkg`
export are implemented.

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

Segment a transcript manifest and write an inspection TSV:

```sh
uv run audawispr segment out/transcript.json --output out/segments.json
```

Enrich a segmented French manifest with IPA:

```sh
uv run audawispr enrich out/segments.json --ipa --output out/enriched.json
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
uv run audawispr clip out/enriched.json --output out/clipped.json --output-dir out/media
```

`clip` reads a segmented or enriched manifest, extracts each segment's audio
from the source file using FFmpeg, and writes the clipped manifest with
`audio_file` paths. By default it reuses existing snippets; use `--force` to
re-clip. Padding (`--padding-before-ms`, `--padding-after-ms`), format
(`--format`), and bitrate (`--bitrate`) are configurable.

Export a clipped manifest for Anki import:

```sh
uv run audawispr export out/clipped.json --format anki-csv --output out/anki-csv
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
uv run audawispr export out/clipped.json --output deck.apkg --deck-name "My French Deck"
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
Because this is a private repository, the workflow keeps routine pushes cheaper:

- Ubuntu runs on pushes and pull requests targeting `master`.
- macOS and Windows run on pull requests targeting `master` and on manual
  `workflow_dispatch` runs.

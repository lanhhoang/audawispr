# audawispr

audawispr splits audio files into high-quality sentence-based learning materials
for language learners. It runs entirely locally — no API keys required.

## Quickstart

```python
from pathlib import Path
from audawispr import Pipeline

Pipeline(
    output=Path("deck.apkg"),
    language="fr",
    ipa=True,
).run(Path("lesson.mp3"))
```

Or from the command line:

```sh
audawispr lesson.mp3 --output deck.apkg --language fr --ipa
```

## Features

- **Transcription** — Local speech-to-text via `faster-whisper`; no API keys needed.
- **Segmentation** — Splits transcriptions into sentence-level segments based on
  punctuation, pauses, and duration bounds.
- **Enrichment** — Optional French IPA phonetic transcription.
- **Clipping** — Extracts audio snippets for each segment using FFmpeg.
- **Export** — Anki-compatible CSV or native `.apkg` packages with embedded audio.
- **One-shot CLI** — Single command runs the full pipeline.

## API Reference

- [Pipeline](api/pipeline.md) — Full pipeline API
- [Exceptions](api/exceptions.md) — Error types
- [CLI](api/cli.md) — Command-line reference

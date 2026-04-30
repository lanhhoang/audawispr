# CLI Reference

The `audawispr` CLI provides subcommands for each pipeline stage and a
one-shot command that runs them all in sequence.

## Global Options

- `--version` — Show version and exit.
- `--verbose` — Print phase names to stderr.

## doctor

Report local runtime readiness.

```sh
audawispr doctor
```

Checks package version, Python version, and FFmpeg/FFprobe availability.

## validate

Validate a transcript manifest schema and timestamps.

```sh
audawispr validate <manifest.json>
```

## transcribe

Transcribe audio locally into a transcript manifest.

```sh
audawispr transcribe <audio> --output out/transcript.json [options]
```

Options:

| Option | Default | Description |
|---|---|---|
| `--language`, `-l` | `fr` | Source language code |
| `--model-size` | `small` | faster-whisper model size or path |
| `--device` | `auto` | Device (`auto`, `cpu`, `cuda`) |
| `--compute-type` | `int8` | Compute type (`int8`, `float16`, `float32`) |
| `--vad/--no-vad` | enabled | Voice activity detection filtering |

## segment

Segment a transcript manifest into sentence-like learning units.

```sh
audawispr segment out/transcript.json --output out/segments.json [options]
```

Options:

| Option | Default | Description |
|---|---|---|
| `--pause-split-ms` | `700` | Pause threshold for splitting (ms) |
| `--min-duration-ms` | `600` | Minimum segment duration (ms) |
| `--max-duration-ms` | `7000` | Maximum segment duration (ms) |
| `--merge-short/--no-merge-short` | enabled | Merge segments shorter than minimum |
| `--inspection-tsv` | auto | Inspection TSV output path |

## enrich

Add optional IPA and translation fields to a segmented manifest.

```sh
audawispr enrich out/segments.json --ipa --output out/enriched.json [options]
```

Options:

| Option | Default | Description |
|---|---|---|
| `--ipa/--no-ipa` | disabled | Generate IPA phonetic transcription (French only) |
| `--translate` | `none` | Translation provider |

## clip

Clip audio snippets from a segmented or enriched manifest.

```sh
audawispr clip out/enriched.json --output out/clipped.json --output-dir out/media [options]
```

Options:

| Option | Default | Description |
|---|---|---|
| `--padding-before-ms` | `150` | Padding before each segment (ms) |
| `--padding-after-ms` | `250` | Padding after each segment (ms) |
| `--format` | `mp3` | Output audio format |
| `--bitrate` | `128k` | Output audio bitrate |
| `--force` | disabled | Re-clip even if snippet exists |

## export

Export a clipped manifest to Anki-compatible format.

```sh
audawispr export out/clipped.json --output out/anki-csv [options]
```

Options:

| Option | Default | Description |
|---|---|---|
| `--format` | `anki-csv` | Export format (`anki-csv` or `apkg`) |
| `--deck-name` | auto | Deck name for APKG export |

For APKG export, the output path must end in `.apkg`:

```sh
audawispr export out/clipped.json --output deck.apkg --deck-name "My French Deck"
```

## One-shot

Run the full pipeline in one command. Unknown positional arguments are
automatically routed to this command.

```sh
audawispr <audio> --output <deck.apkg> [options]
```

Accepts all options from the individual subcommands. The pipeline runs
transcription, segmentation, enrichment, clipping, and export in sequence.

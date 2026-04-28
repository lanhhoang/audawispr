# Phase 2: Local Transcription To Manifest

## Goal

Add versioned manifest models and local `faster-whisper` transcription. After
this phase, users can turn an audio file into a validated JSON transcript
manifest without any transcription API key.

## User-Usable Result

- `uv run audawispr transcribe AUDIO --output out/transcript.json --language fr`
  writes a manifest containing source audio metadata, transcription settings,
  raw segment text, timestamps, and word timestamps.
- `uv run audawispr validate out/transcript.json` validates schema and segment
  timing.

## TODO

- [ ] Add `faster-whisper`, `onnxruntime`, and `pydantic` runtime
  dependencies.
- [ ] Define manifest models with schema version, app version, timestamps,
  language, source audio metadata, transcription settings, segments, and words.
- [ ] Implement manifest save/load/validation helpers with atomic JSON writes.
- [ ] Add `audawispr validate MANIFEST` for strict schema and timestamp
  validation.
- [ ] Implement source audio metadata generation including file name, absolute
  path, size, SHA-256, language, and optional duration.
- [ ] Implement transcription core using `faster-whisper` with word timestamps
  and VAD enabled by default.
- [ ] Treat missing word timestamps from transcription as a transcription error,
  because Phase 3 segmentation requires them.
- [ ] Add `audawispr transcribe` CLI options for input path, output path,
  language, model size, device, compute type, and VAD.
- [ ] Add clear errors for missing input audio, missing dependency, model
  initialization failure, and invalid generated manifest.
- [ ] Add tests with fake Whisper output to avoid requiring real model downloads
  in unit tests.

## Defaults

- `language=fr`
- `model_size=small`
- `device=auto`
- `compute_type=default`
- `vad=true`
- `word_timestamps=true`

## Acceptance Checks

- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr transcribe --help`
- [ ] `uv run audawispr validate --help`

## Notes

- First-time model download may require network, but no transcription API key is
  required.
- Word timestamps are required in Epic 1. Do not add segment-level fallback
  segmentation unless a later plan explicitly changes that policy.
- Do not implement segmentation, IPA, clipping, or export in this phase.

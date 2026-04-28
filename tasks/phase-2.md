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
- [ ] Confirm dependency resolution for `faster-whisper` and `onnxruntime` in CI
  on Linux, macOS, and Windows without downloading Whisper models.
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
- [ ] Ensure CI transcription tests use fakes or mocks and never download Whisper
  models.
- [ ] Update README with `transcribe` and `validate` command usage.

## Defaults

- `language=fr`
- `model_size=small`
- `device=auto`
- `compute_type=int8`
- `vad=true`
- `word_timestamps=true`
- `compute_type` is a default, not a restriction; the CLI must allow override
  for GPU or platform-specific faster-whisper setups.

## Acceptance Checks

- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr transcribe --help`
- [ ] `uv run audawispr validate --help`
- [ ] CI quality workflow passes.
- [ ] README documents Phase 2 commands.

## Notes

- First-time model download may require network, but no transcription API key is
  required.
- Store source audio paths as strings from `Path.resolve()` for local reruns.
  Do not treat those absolute paths as portable across machines.
- Word timestamps are required in Epic 1. Do not add segment-level fallback
  segmentation unless a later plan explicitly changes that policy.
- Do not implement segmentation, IPA, clipping, or export in this phase.

## Verification Evidence

- Pending.

## Actual Implementation

Phase 2 can start from the current Phase 1 baseline. The branch is clean, matches
`master`, and the existing Phase 1 checks pass locally:

- `uv sync --dev --frozen`
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check src tests`

Use the following implementation order so the feature stays usable and testable
while it is being built:

- [ ] Add runtime dependencies: `faster-whisper`, `onnxruntime`, and
  `pydantic>=2`.
- [ ] Confirm `uv sync --dev` and `uv sync --dev --frozen` resolve dependencies
  without downloading Whisper models.
- [ ] Add Pydantic v2 manifest models for schema version, app version,
  creation timestamp, source audio metadata, transcription settings, language,
  segments, and words.
- [ ] Validate manifest timing with non-negative timestamps, `start <= end`, and
  word timestamps inside segment bounds where available.
- [ ] Implement atomic JSON save/load helpers using a temporary file in the
  destination directory followed by replace.
- [ ] Implement source audio metadata collection for file name, resolved absolute
  path string, byte size, SHA-256, language, and best-effort duration.
- [ ] Keep duration optional: use FFprobe when available, but do not fail
  transcription solely because duration cannot be read.
- [ ] Fail before model initialization when input audio is missing, is a
  directory, or cannot be read.
- [ ] Add a transcription backend boundary so tests can inject fake Whisper
  output and future `whisper.cpp` support can reuse the CLI contract.
- [ ] Implement the `faster-whisper` backend with defaults:
  `language=fr`, `model_size=small`, `device=auto`, `compute_type=int8`,
  `vad=true`, and `word_timestamps=true`.
- [ ] Materialize the Whisper segment generator before writing the manifest so
  transcription errors surface before any final output file is replaced.
- [ ] Treat missing word timestamps as a hard transcription error.
- [ ] Add `audawispr transcribe AUDIO --output out/transcript.json --language fr`
  with options for model size, device, compute type, and VAD.
- [ ] Add `audawispr validate MANIFEST` for strict schema and timestamp
  validation.
- [ ] Map common failures to clear CLI errors with non-zero exits: missing input,
  invalid manifest, missing dependency, model initialization failure,
  transcription failure, and output write failure.
- [ ] Add tests for manifest validation, atomic save/load, source metadata, fake
  transcription output, missing word timestamps, CLI help, CLI validation
  success/failure, and CLI transcribe using a fake backend.
- [ ] Ensure normal CI imports and tests transcription code without downloading
  Whisper models.
- [ ] Update `README.md` with Phase 2 usage and note that first real model use
  may download model files.
- [ ] After implementation, update this phase's verification evidence and mark
  Phase 2 complete in `tasks/epic-1.md`.

Implementation assumptions:

- Use Pydantic v2 models rather than dataclasses because Phase 2 requires strict
  schema validation.
- Keep generated `transcript.json` ignored by git, as already configured.
- Do not add segmentation, IPA, clipping, CSV, or APKG behavior in Phase 2.

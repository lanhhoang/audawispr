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

- [x] Add `faster-whisper`, `onnxruntime`, and `pydantic` runtime
  dependencies.
- [x] Confirm dependency resolution for `faster-whisper` and `onnxruntime`
  locally without downloading Whisper models. Remote Linux, macOS, and Windows
  CI confirmation is pending.
- [x] Define manifest models with schema version, app version, timestamps,
  language, source audio metadata, transcription settings, segments, and words.
- [x] Implement manifest save/load/validation helpers with atomic JSON writes.
- [x] Add `audawispr validate MANIFEST` for strict schema and timestamp
  validation.
- [x] Implement source audio metadata generation including file name, absolute
  path, size, SHA-256, language, and optional duration.
- [x] Implement transcription core using `faster-whisper` with word timestamps
  and VAD enabled by default.
- [x] Treat missing word timestamps from transcription as a transcription error,
  because Phase 3 segmentation requires them.
- [x] Add `audawispr transcribe` CLI options for input path, output path,
  language, model size, device, compute type, and VAD.
- [x] Add clear errors for missing input audio, missing dependency, model
  initialization failure, and invalid generated manifest.
- [x] Add tests with fake Whisper output to avoid requiring real model downloads
  in unit tests.
- [x] Ensure CI transcription tests use fakes or mocks and never download Whisper
  models.
- [x] Update README with `transcribe` and `validate` command usage.

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

- [x] `uv run pytest`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run ty check src tests`
- [x] `uv run audawispr transcribe --help`
- [x] `uv run audawispr validate --help`
- [ ] CI quality workflow passes.
- [x] README documents Phase 2 commands.

## Notes

- First-time model download may require network, but no transcription API key is
  required.
- Store source audio paths as strings from `Path.resolve()` for local reruns.
  Do not treat those absolute paths as portable across machines.
- Word timestamps are required in Epic 1. Do not add segment-level fallback
  segmentation unless a later plan explicitly changes that policy.
- Do not implement segmentation, IPA, clipping, or export in this phase.

## Verification Evidence

- `uv sync --dev` resolved dependencies with `onnxruntime==1.22.1`, avoiding
  the latest ONNX Runtime wheel line that does not support macOS x86_64.
- `uv sync --dev --frozen` passed.
- `uv run pytest` passed: 21 tests.
- `uv run ruff check .` passed.
- `uv run ty check src tests` passed.
- `uv run audawispr transcribe --help` passed.
- `uv run audawispr validate --help` passed.
- `uv run ruff format --check .` passed: 16 files already formatted.
- Remote CI is pending.

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

- [x] Add runtime dependencies: `faster-whisper`, `onnxruntime`, and
  `pydantic>=2`.
- [x] Confirm `uv sync --dev` and `uv sync --dev --frozen` resolve dependencies
  without downloading Whisper models.
- [x] Add Pydantic v2 manifest models for schema version, app version,
  creation timestamp, source audio metadata, transcription settings, language,
  segments, and words.
- [x] Validate manifest timing with non-negative timestamps, `start <= end`, and
  word timestamps inside segment bounds where available.
- [x] Implement atomic JSON save/load helpers using a temporary file in the
  destination directory followed by replace.
- [x] Implement source audio metadata collection for file name, resolved absolute
  path string, byte size, SHA-256, language, and best-effort duration.
- [x] Keep duration optional: use FFprobe when available, but do not fail
  transcription solely because duration cannot be read.
- [x] Fail before model initialization when input audio is missing, is a
  directory, or cannot be read.
- [x] Add a transcription backend boundary so tests can inject fake Whisper
  output and future `whisper.cpp` support can reuse the CLI contract.
- [x] Implement the `faster-whisper` backend with defaults:
  `language=fr`, `model_size=small`, `device=auto`, `compute_type=int8`,
  `vad=true`, and `word_timestamps=true`.
- [x] Materialize the Whisper segment generator before writing the manifest so
  transcription errors surface before any final output file is replaced.
- [x] Treat missing word timestamps as a hard transcription error.
- [x] Add `audawispr transcribe AUDIO --output out/transcript.json --language fr`
  with options for model size, device, compute type, and VAD.
- [x] Add `audawispr validate MANIFEST` for strict schema and timestamp
  validation.
- [x] Map common failures to clear CLI errors with non-zero exits: missing input,
  invalid manifest, missing dependency, model initialization failure,
  transcription failure, and output write failure.
- [x] Add tests for manifest validation, atomic save/load, source metadata, fake
  transcription output, missing word timestamps, CLI help, CLI validation
  success/failure, and CLI transcribe using a fake backend.
- [x] Ensure normal CI imports and tests transcription code without downloading
  Whisper models.
- [x] Update `README.md` with Phase 2 usage and note that first real model use
  may download model files.
- [ ] After implementation, update this phase's verification evidence and mark
  Phase 2 complete in `tasks/epic-1.md` after remote CI passes.

Implementation assumptions:

- Use Pydantic v2 models rather than dataclasses because Phase 2 requires strict
  schema validation.
- Keep generated `transcript.json` ignored by git, as already configured.
- Do not add segmentation, IPA, clipping, CSV, or APKG behavior in Phase 2.

# Phase 8: One-Shot CLI + Python Facade

## Goal

Wire the implemented phases into a full one-shot CLI command and a narrow
Python facade for future apps. After this phase, users can create an Anki deck
directly from an audio file with one command.

## User-Usable Result

- `uv run audawispr AUDIO --output deck.apkg --language fr --ipa` runs
  transcription, segmentation, enrichment, clipping, and export.
- `Pipeline(output=Path("deck.apkg"), language="fr").run(Path("audio.mp3"), ipa=True)`
  provides the same simple path for Python callers.

## TODO

- [ ] Add core pipeline request/result types for one-shot execution.
- [ ] Add progress event and progress hook types suitable for CLI and future app
  wrappers.
- [ ] Implement pipeline orchestration over transcribe, segment, enrich, clip,
  and export phases.
- [ ] Store intermediate manifests and snippets under a work directory for
  reruns and debugging.
- [ ] Add root Typer callback/command for `audawispr AUDIO --output deck.apkg`.
- [ ] Add simple `audawispr.pipeline.Pipeline` facade.
- [ ] Add phase-specific error wrapping with actionable messages.
- [ ] Ensure manifest-based phase commands from earlier phases keep working.
- [ ] Update README with full quickstart and phase command examples.

## Defaults

- Output path ending in `.apkg` implies native APKG export.
- Intermediate work directory is derived from the output path.
- Translation remains `none` only in Epic 1.

## Acceptance Checks

- [ ] One-shot CLI tests with mocked transcription.
- [ ] Python facade tests.
- [ ] Tests for intermediate output paths.
- [ ] Tests for phase-specific error messages.
- [ ] Regression tests for all phase subcommands.
- [ ] `uv run pytest`
- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run ty check src tests`
- [ ] `uv run audawispr --help`
- [ ] `uv run audawispr doctor`

## Notes

- This phase completes Epic 1 but should not add live translation providers.
- Web and desktop wrappers remain later epics.

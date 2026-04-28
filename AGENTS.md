# Repository Guidelines

## Project Structure & Module Organization

This repo is currently plan-first. Roadmap and phase details live in `tasks/`,
with `tasks/epic-1.md` as the main dashboard and `tasks/phase-N.md` files for
phase-level work.

The planned Python package uses a `src/` layout:

- `src/audawispr/`: package source and Typer CLI entrypoint
- `src/audawispr/core/`: reusable transcription, segmentation, enrichment,
  clipping, export, manifest, and pipeline logic
- `tests/`: pytest tests and fixtures
- `README.md`: user-facing setup and command documentation

## Build, Test, and Development Commands

After Phase 1 scaffolding, use:

- `uv sync --dev`: install runtime and development dependencies.
- `uv run audawispr --help`: verify the CLI is installed.
- `uv run audawispr doctor`: check Python and FFmpeg/FFprobe readiness.
- `uv run pytest`: run the test suite.
- `uv run ruff check .`: run lint checks.
- `uv run ruff format --check .`: verify formatting.
- `uv run ty check src tests`: run type checks.

CI must run tests, lint, format check, and typecheck on Linux, macOS, and
Windows.

## Coding Style & Naming Conventions

Target Python 3.11+. Use 4-space indentation, type hints, and `Path` for
filesystem values. Keep filesystem/process code cross-platform for macOS, Linux,
and Windows.

Use `snake_case` for functions, modules, and variables. Use `PascalCase` for
classes. Prefer clear dataclasses or Pydantic models for structured data.

Do not register visible CLI commands before their phase implements them.

## Testing Guidelines

Use pytest. Test files should be named `tests/test_*.py`, and test functions
should be named `test_*`.

Keep heavyweight behavior mocked in normal CI: Whisper model downloads and real
FFmpeg smoke tests should not be required for the default test suite. Add
focused tests for manifest validation, CLI behavior, cross-platform path
handling, and error paths.

## Commit & Pull Request Guidelines

Follow the existing commit style, for example:

- `docs: update task documentation for phases 1-8`
- `feat: initialize project structure`
- `chore: add segments.json to gitignore`
- `refactor: reorganize implementation plan`

Keep commits scoped to one logical change. Pull requests should include a short
summary, linked task or phase, verification commands run, and any skipped checks
with reasons.

## Security & Configuration Tips

Do not commit generated manifests, audio snippets, APKG files, model caches,
virtual environments, or machine-specific paths.

Use `AUDAWISPR_FFMPEG` and `AUDAWISPR_FFPROBE` for explicit FFmpeg tool paths.
Network translation providers are out of scope for Epic 1 unless a later plan
adds them.

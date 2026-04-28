# Phase 1: Project Foundation + Diagnostics

## Goal

Deliver a runnable Python package with a Typer CLI, reusable package structure,
development tooling, and diagnostics. After this phase, users can verify the app
is installed and inspect local runtime readiness.

## User-Usable Result

- `uv run audawispr --help` displays the CLI.
- `uv run audawispr --version` displays the package version.
- `uv run audawispr doctor` reports Python/package readiness and FFmpeg/FFprobe
  availability.

## TODO

- [x] Scaffold `pyproject.toml` with `hatchling`, `uv`, Python 3.11+,
  `typer`, `static-ffmpeg`, `pytest`, `ruff`, and `ty`.
- [x] Add package skeleton under `src/audawispr/` with `__init__.py`,
  `__about__.py`, `__main__.py`, and `cli.py`.
- [x] Add `tests/` with at least one passing CLI/package smoke test so Phase 1
  quality commands have real test input.
- [x] Add `.gitignore` entries for `.venv/`, Python caches, tool caches,
  Whisper/model caches, generated manifests, snippets, decks, and output
  directories.
- [x] Add a Typer app with `--version` and `doctor`. Do not register visible
  future commands until their phases implement them.
- [x] Add a small diagnostics core that checks Python version, package version,
  and FFmpeg/FFprobe availability from `AUDAWISPR_FFMPEG`,
  `AUDAWISPR_FFPROBE`, `PATH`, or static-ffmpeg.
- [x] Ensure diagnostics work with Windows `.exe` tool paths as well as macOS
  and Linux binaries.
- [x] Add initial CI quality workflow targeting Linux, macOS, and Windows for
  tests, lint, format check, and typecheck on `push` and `pull_request`.
- [x] Add initial tests for CLI help, version output, and doctor output shape.
- [x] Update README with installation and Phase 1 diagnostics usage.

## Defaults

- Phase 1 diagnostics detect and report FFmpeg/FFprobe availability only. Do not
  implement managed FFmpeg installation in Epic 1 unless a later plan adds it.
- `static-ffmpeg` is allowed only as a local binary provider/detection fallback
  in Epic 1; it must not imply an installer command.
- If static-ffmpeg cannot provide binaries for the current OS, `doctor` should
  report that cleanly and continue checking other sources.

## Acceptance Checks

- [x] `uv run pytest`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run ty check src tests`
- [x] `uv run audawispr --help`
- [x] `uv run audawispr --version`
- [x] `uv run audawispr doctor`
- [x] CI quality workflow exists for Linux, macOS, and Windows and runs
  `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and
  `uv run ty check src tests`.
- [x] CI workflow triggers on `push` and `pull_request`.

## Notes

- Do not implement transcription or manifest behavior in this phase.
- Keep diagnostics useful even when FFmpeg is missing; missing tools should be
  reported, not crash the command.
- Do not commit generated transcription output, snippets, APKG files, model
  caches, or machine-specific paths.

## Verification Evidence

- `uv sync --dev` completed successfully.
- `uv run pytest` passed: 5 tests.
- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed.
- `uv run ty check src tests` passed.
- `uv run audawispr --help` passed and shows only the implemented `doctor`
  command.
- `uv run audawispr --version` passed and reports `audawispr 0.1.0`.
- `uv run audawispr doctor` passed and reports package, Python, FFmpeg, and
  FFprobe readiness.
- CI workflow added at `.github/workflows/quality.yml` for Linux, macOS, and
  Windows on `push` and `pull_request`.

## Actual Implementation

### Current Readiness

- The repo is ready to start Phase 1: the working tree is clean and the branch
  is `epic-1-phase-1-project-foundation-diagnostics`.
- The repo is currently docs-only: there is no `pyproject.toml`, `src/`,
  `tests/`, `.github/workflows/`, package entrypoint, CLI, diagnostics core, or
  lockfile.
- `.gitignore` already covers common Python and tool caches, but still needs
  audawispr-specific generated outputs, model caches, media snippets, decks, and
  output directories.
- `README.md` only has a title and short description, so Phase 1 usage docs
  need to be added from scratch.

### Execution Plan

- Add Python packaging with `pyproject.toml`, `hatchling`, Python `>=3.11`,
  Typer, `static-ffmpeg`, pytest, ruff, ty, the `audawispr` console script, and
  an initial `uv.lock`.
- Add the package skeleton under `src/audawispr/`, including `__init__.py`,
  `__about__.py`, `__main__.py`, `cli.py`, and a small diagnostics module under
  `src/audawispr/core/`.
- Implement only Phase 1 CLI behavior: root help, `--version`, and `doctor`.
  Do not expose future commands before their phases implement them.
- Implement diagnostics for package version, Python version, FFmpeg, and
  FFprobe. Discovery order is explicit environment variables
  `AUDAWISPR_FFMPEG` and `AUDAWISPR_FFPROBE`, then `PATH`, then guarded
  `static-ffmpeg` fallback.
- Keep diagnostics cross-platform by using `Path`, `shutil.which`, and
  `subprocess.run([...], shell=False)`. Missing FFmpeg or FFprobe should be
  reported cleanly instead of crashing `doctor`.
- Add pytest smoke coverage for package import/version, CLI help, version
  output, and doctor output shape. Mock binary discovery where needed so CI does
  not depend on local FFmpeg installs.
- Add a GitHub Actions workflow for `push` and `pull_request` on Linux, macOS,
  and Windows. CI must run `uv sync --dev`, `uv run pytest`,
  `uv run ruff check .`, `uv run ruff format --check .`, and
  `uv run ty check src tests`.
- Expand `.gitignore` with generated manifests, snippets/media, APKG/deck
  outputs, output directories, and Whisper/model caches.
- Update `README.md` with Phase 1 install, CLI help, version, and diagnostics
  usage.
- After checks pass, update this file's verification evidence and mark Phase 1
  complete in `tasks/epic-1.md`.

### Verification Plan

- `uv sync --dev`
- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run ty check src tests`
- `uv run audawispr --help`
- `uv run audawispr --version`
- `uv run audawispr doctor`

### Implementation Assumptions

- Use Python 3.11 as the first supported CI version.
- Commit `uv.lock` because audawispr is an application-style CLI project.
- Do not add transcription, manifests, segmentation, or Anki export behavior in
  Phase 1.
- Do not require FFmpeg or FFprobe to be installed for tests or for `doctor` to
  complete successfully.

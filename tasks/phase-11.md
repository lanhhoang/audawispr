# Phase 11: PyPI Publishing Preparation

## Goal

Prepare the `audawispr` package for first-time publishing to PyPI by adding
required metadata, creating a license, improving the README, and completing
the public Python API surface.

## TODO

### Group A — Code Changes

- [ ] A1: Add `authors`, `license` fields to `pyproject.toml` under `[project]`
- [ ] A2: Add `[project.urls]` block with `Homepage` and `Repository`
- [ ] A3: Add `classifiers` and `keywords` to `pyproject.toml`
- [ ] A4: Re-export `Pipeline` from `src/audawispr/__init__.py`
- [ ] A5: Re-export exception classes (`AudawisprError`, `InputAudioError`, `ManifestError`, etc.) from `src/audawispr/__init__.py`
- [ ] A6: Create `.github/workflows/release.yml` with Trusted Publisher OIDC config

### Group B — Documentation Changes

- [ ] B1: Create `LICENSE` file (MIT) at repo root
- [ ] B2: Add `pip install audawispr` and `uv pip install audawispr` to README Setup section
- [ ] B3: Add CI status badge and Python version badge to README

## Defaults

- License: MIT
- `authors`: `[{ name = "Lanh Hoang" }]`
- Publishing: GitHub Actions Trusted Publisher via OIDC (no API tokens)
- Workflow file: `.github/workflows/release.yml`
- Trigger: `on: push: tags: ["v*"]`
- Release tag: `v0.1.0`
- `classifiers`: `Development Status :: 3 - Alpha`, `Programming Language :: Python :: 3.11`, `Programming Language :: Python :: 3.12`, `Programming Language :: Python :: 3.13`, `Topic :: Multimedia :: Sound/Audio`, `Topic :: Education`, `Intended Audience :: Education`, `License :: OSI Approved :: MIT License`
- `keywords`: `anki, language-learning, transcription, whisper, flashcards, audio, anki-deck, apkg, spaced-repetition`
- `[project.urls]`: Homepage and Repository pointing to the GitHub URL

## Acceptance Checks

- [ ] `uv build` produces a valid `.whl` and `.tar.gz` in `dist/`
- [ ] `uv run python -c "from audawispr import Pipeline"` succeeds
- [ ] `uv run python -c "from audawispr import AudawisprError, ManifestError"` succeeds
- [ ] `README.md` contains `pip install audawispr` command
- [ ] `LICENSE` file exists at repo root
- [ ] `pyproject.toml` has `authors`, `license`, `urls`, `classifiers`, `keywords` fields
- [ ] Full test suite (143/143), lint, format, typecheck all green
- [ ] `.github/workflows/release.yml` exists with OIDC publish step

## Implementation Plan

### Execution Groups

| Group | Items | Description |
|-------|-------|-------------|
| G1 | B1, B3 | Create LICENSE, add README badges |
| G2 | A1, A2, A3, A6 | pyproject.toml metadata + release workflow |
| G3 | A4, A5 | Re-export public API symbols |
| G4 | B2 | Update README Setup section |
| Verify | Build + test | `uv build`, `uv run pytest`, import checks |

### Execution Order

G1 → G2 → G3 → G4 → Verify (all parallel within group, G2+G3 can run concurrently)

## Decisions

- **Version**: `v0.1.0` — using Semantic Versioning (SemVer), not Calendar Versioning (CalVer). SemVer gives `pip` meaningful compatibility signals (`>=0.1.0,<0.2.0`).
- **Publisher**: GitHub Actions Trusted Publisher (OIDC) — no API tokens to manage. One-time PyPI setup: add `lanhhoang/audawispr-three` repo with workflow `release.yml`.
- **Workflow name**: `release.yml` (not `publish.yml` or `pypipublish.yml`).
- **whisper.cpp backend**: Deferred to separate epic. `pywhispercpp` (v1.4.1) confirmed as viable binding — pre-built CPU wheels cross-platform, MIT license, clean API matching existing `TranscriptionBackend` protocol.
- **Docs directory**: Optional — deferred. README is thorough enough for initial PyPI page.

## Verification Evidence

(to be filled after implementation)

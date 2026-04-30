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

| Group  | Items          | Description                                |
| ------ | -------------- | ------------------------------------------ |
| G1     | B1, B3         | Create LICENSE, add README badges          |
| G2     | A1, A2, A3, A6 | pyproject.toml metadata + release workflow |
| G3     | A4, A5         | Re-export public API symbols               |
| G4     | B2             | Update README Setup section                |
| Verify | Build + test   | `uv build`, `uv run pytest`, import checks |

### Execution Order

G1 → G2 → G3 → G4 → Verify (all parallel within group, G2+G3 can run concurrently)

## Decisions

- **Version**: `v0.1.0` — using Semantic Versioning (SemVer), not Calendar Versioning (CalVer). SemVer gives `pip` meaningful compatibility signals (`>=0.1.0,<0.2.0`).
- **Publisher**: GitHub Actions Trusted Publisher (OIDC) — no API tokens to manage. One-time PyPI setup: add `lanhhoang/audawispr` repo with workflow `release.yml`.
- **Workflow name**: `release.yml` (not `publish.yml` or `pypipublish.yml`).
- **whisper.cpp backend**: Deferred to separate epic. `pywhispercpp` (v1.4.1) confirmed as viable binding — pre-built CPU wheels cross-platform, MIT license, clean API matching existing `TranscriptionBackend` protocol.
- **Docs directory**: Optional — deferred. README is thorough enough for initial PyPI page.

## Verification Evidence

(to be filled after implementation)

## Actual Implementation

### Readiness (2026-04-29)

Four-agent review (analyzer, researcher, architect, verifier) confirmed **GO**:

- **Phases 1–10** complete, merged to `master`, CI green (143/143 tests, lint/format/typecheck clean)
- **0 of 9** Phase 11 items started — clean branch `epic-1-phase-11-pypi-publishing-preparation`
- **Repo renamed** from `audawispr-three` to `audawispr` (`github.com:lanhhoang/audawispr.git`)
- `uv build` already produces valid `audawispr-0.1.0.tar.gz` and `.whl` artifacts

### Prioritized Execution Order

| Step   | Items          | Description                                    | Depends On                        | Parallel?           |
| ------ | -------------- | ---------------------------------------------- | --------------------------------- | ------------------- |
| **1**  | B1, B3         | Create LICENSE (MIT) + README badges           | None                              | —                   |
| 2      | A1, A2, A3, A6 | pyproject.toml metadata + release.yml          | Step 1                            | Can run with Step 3 |
| 3      | A4, A5         | Re-export Pipeline + exceptions in **init**.py | None (logically independent)      | Can run with Step 2 |
| 4      | B2             | Add pip install / uv pip install to README     | Steps 2, 3 (for accurate content) | —                   |
| Verify | All            | Build, imports, tests, lint, format, typecheck | Steps 1–4                         | Sequential          |

**Rationale:** G1 first because LICENSE must exist before `pyproject.toml` references it (`license = {text = "MIT"}`). G2 and G3 independent — can run concurrently. G4 deferred until metadata and API surface are settled.

### Risks to Address During Implementation

| #   | Risk                                                                                                          | Mitigation                                                                                                     |
| --- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| R1  | CI matrix only runs Python 3.11 but classifiers claim 3.11/3.12/3.13 — claiming support without test coverage | Either add 3.12/3.13 to CI matrix in quality.yml, or trim classifiers to 3.11 only for v0.1.0 and expand later |
| R2  | README references "private repository" — misleading once public on PyPI                                       | Update or remove the private-repo note during B2                                                               |
| R3  | Trusted Publisher needs manual PyPI-side setup before first `v0.1.0` tag push                                 | Pre-flight: configure lanhhoang/audawispr + release.yml in PyPI project settings                               |
| R4  | `onnxruntime` upper pin (`<1.23`) may cause install conflicts on newer Python                                 | Acceptable for v0.1.0; loosen in follow-up if needed                                                           |

### Pre-Flight (Before Tag Push)

- [ ] Log into https://pypi.org/ → Project Settings → Trusted Publisher
- [ ] Add: Owner = `lanhhoang`, Repo = `audawispr`, Workflow = `release.yml`
- [ ] Ensure project name `audawispr` is reserved (create empty project if needed)

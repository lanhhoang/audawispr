# audawispr agent guidelines

Single-package Python CLI + library. Build system: `hatchling`. Package manager: `uv`.

## Commands

```sh
uv sync --dev            # install dev deps (pytest, ruff, ty)
uv run pytest            # run all tests
uv run python -m pytest  # fallback if `uv run pytest` fails with ENOENT
uv run ruff check .      # lint (select: E/F/I/UP/B, line-length 88)
uv run ruff format --check .
uv run ty check src tests
audawispr --help         # after `uv sync`, verifies CLI installed
audawispr doctor         # checks Python + FFmpeg/FFprobe readiness
```

Commit-triggered CI runs the same four checks (tests, lint, format, typecheck) on Linux, macOS, Windows.

## CLI quirk

The CLI uses `_OneShotFallbackGroup` — unknown positional args auto-route to the hidden `_oneshot` command. So `audawispr lesson.mp3 --output deck.apkg` works without a subcommand.

## Architecture

- **Entrypoint**: `src/audawispr/cli.py` (Typer app), wire-up in `pyproject.toml: [project.scripts] audawispr = "audawispr.cli:app"`
- **Public API**: `audawispr.Pipeline` — wraps the full pipeline (`__init__.py` re-exports it + 10 exception classes)
- **Modules**: `core/` has one file per pipeline stage (`transcription.py`, `segmentation.py`, `enrichment.py`, `clipping.py`, `export.py`) + shared models (`manifest.py`) + errors (`errors.py`) + diagnostics (`diagnostics.py`)
- **Version**: single source in `src/audawispr/__about__.py`

## Testing

- Pytest, no conftest plugins beyond default. Test files: `tests/test_*.py`.
- Heavy operations (Whisper model download, real FFmpeg) must be mocked in CI. Focus tests on manifest validation, CLI behavior, path handling, error paths.

## Notable

- `static-ffmpeg` is a Python dependency — FFmpeg binaries bundled via pip. Override with `AUDAWISPR_FFMPEG` / `AUDAWISPR_FPROBE` env vars.
- Release workflow uses Trusted Publisher OIDC (`pypa/gh-action-pypi-publish@release/v1`, `permissions: id-token: write`) — no API token.
- onnxruntime macOS Intel is pinned to v1.23.2 (last x86_64 wheel). Apple Silicon gets latest. Both satisfy `>=1.22.1,<2.0`.

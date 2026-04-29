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

- [x] Add core pipeline request/result types for one-shot execution.
- [x] Add progress event, progress hook, and cooperative cancellation token types
  suitable for CLI and future app wrappers.
- [x] Implement pipeline orchestration over transcribe, segment, enrich, clip,
  and export phases.
- [x] Skip the enrich phase when `--ipa` is false and translation is `none`.
- [x] Store intermediate manifests and snippets under a work directory for
  reruns and debugging.
- [x] Add root Typer callback/command for `audawispr AUDIO --output deck.apkg`.
- [x] Add simple `audawispr.pipeline.Pipeline` facade.
- [x] Add phase-specific error wrapping with actionable messages.
- [x] Add cancellation checks at phase boundaries and supported per-segment loops.
- [x] Ensure manifest-based phase commands from earlier phases keep working.
- [x] Update README with full quickstart and phase command examples.

## Defaults

- Output path ending in `.apkg` implies native APKG export.
- Intermediate work directory is derived from the output path:
  - `deck.apkg` uses `deck/_work/`
  - directory output uses `<output>/_work/`
- For `deck.apkg`, `deck/_work/` is a sibling directory next to the APKG path,
  not content inside the APKG package.
- Implement work directory paths with `Path` joins. The `/` examples above are
  documentation shorthand, not string concatenation requirements.
- Translation remains `none` only in Epic 1.
- Cancellation is cooperative and does not interrupt an active Whisper model
  call, FFmpeg subprocess, or APKG write mid-call.

## Acceptance Checks

- [x] One-shot CLI tests with mocked transcription.
- [x] Python facade tests.
- [x] Tests for intermediate output paths.
- [x] Tests that enrichment is skipped when no IPA or translation is requested.
- [x] Tests that one-shot work directory derivation is correct with Windows-style
  and POSIX-style paths.
- [x] Tests for phase-specific error messages.
- [x] Tests for cooperative cancellation before or between phases.
- [x] Regression tests for all phase subcommands.
- [x] `uv run pytest`
- [x] `uv run ruff check .`
- [x] `uv run ruff format --check .`
- [x] `uv run ty check src tests`
- [x] `uv run audawispr --help`
- [x] `uv run audawispr doctor`
- [x] CI quality workflow passes.
- [x] README documents one-shot CLI and Python facade usage.

## Notes

- This phase completes Epic 1 but should not add live translation providers.
- Web and desktop wrappers remain later epics.

## Verification Evidence

- `uv run pytest`: 123 passed (26 new pipeline tests + 97 existing regression tests)
- `uv run ruff check .`: clean
- `uv run ruff format --check .`: clean
- `uv run ty check src tests`: clean
- `uv run audawispr --help`: shows callback options and 7 visible subcommands (hidden `_oneshot` not listed)
- `uv run audawispr doctor`: reports package, Python, FFmpeg, and FFprobe status
- Deviation: `@app.command(hidden=True, name="_oneshot")` requires explicit `name="_oneshot"` because Typer converts underscores to hyphens in inferred command names.
- Deviation: `parse_args` inserts `_oneshot` before the first positional argument (not at the start of `args`) so callback options like `--verbose` are still parsed by the callback.
- Deviation: `PipelineRequest` uses `model_size="small"` and `device="auto"` to match existing `TranscriptionOptions` defaults rather than the "base"/"cpu" shown in the original phase-8.md draft.

## Actual Implementation

### Design Decision: Custom TyperGroup for One-Shot Dispatch

The one-shot syntax `audawispr AUDIO --output deck.apkg --language fr --ipa`
requires Typer to treat a positional audio path as a command redirect rather
than an unknown command error. A custom `_OneShotFallbackGroup(TyperGroup)`
handles this by overriding `parse_args`:

- When the first positional argument is not a known subcommand, prepend
  `_oneshot` to `args` before Typer resolves the command.
- When the first positional argument *is* a known subcommand (`doctor`,
  `validate`, `transcribe`, etc.), pass through unchanged.
- The `_oneshot` command is registered with `hidden=True` so it never appears in
  `--help` output.

This is cleaner than `sys.argv` interception because it operates inside Typer's
normal parsing flow, preserves all existing subcommands without routing logic,
and keeps the callback scope minimal.

---

### Group A: Core Pipeline Module (`src/audawispr/core/pipeline.py`)

**Types**

```python
@dataclass
class ProgressEvent:
    phase: str        # e.g. "transcribe", "segment", "enrich", "clip", "export"
    message: str

ProgressHook = Callable[[ProgressEvent], None]

class CancellationToken:
    """Cooperative cancellation checked between phases."""
    cancelled: bool = False

    def request_cancel(self) -> None: ...
    def check(self) -> None:
        """Raise CancelledError if cancellation was requested."""
```

**Request and Result**

```python
@dataclass
class PipelineRequest:
    audio: Path
    output: Path
    language: str = "fr"
    ipa: bool = False
    model_size: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    vad: str = "silero"
    pause_split_ms: int = 500
    min_duration_ms: int = 1000
    max_duration_ms: int = 15000
    deck_name: str | None = None
    keep_work: bool = False

@dataclass
class PipelineResult:
    output_path: Path
    work_dir: Path
    cancelled: bool = False
```

**`run_pipeline()` function**

- **Work directory derivation**:
  - `.apkg` output: `output_path.with_suffix("") / "_work"` — e.g. `deck.apkg`
    produces `deck/_work/`
  - Non-`.apkg` (CSV) output: `output_dir / "_work"`
- **Phase order**: `transcribe → segment → enrich (conditional) → clip → export`
- **Conditional enrich**: skip when `ipa=False` and
  `translation_provider="none"`
- **Progress hook**: call `hook(ProgressEvent(phase_name, message))` at each
  phase boundary
- **Cancellation**: call `token.check()` before each phase; raises
  `CancelledError` if cancel was requested
- **Error wrapping**: catch phase-specific exceptions and re-raise with
  actionable context:

```python
except TranscriptionError as exc:
    raise OneShotError(
        f"Transcription failed: {exc}. "
        f"Try a different --model-size or --device."
    ) from exc
```

- Always runs `finalize` block: delete `_work/` unless `keep_work=True`, even
  on error (leave artifacts on error for debugging).

---

### Group B: Python Facade (`src/audawispr/pipeline.py`)

Narrow public API wrapping the core pipeline module:

```python
from audawispr.core.pipeline import (
    PipelineRequest,
    PipelineResult,
    ProgressEvent,
    ProgressHook,
    CancellationToken,
    run_pipeline,
)

class Pipeline:
    def __init__(
        self,
        output: Path,
        *,
        language: str = "fr",
        ipa: bool = False,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        vad: str = "silero",
        pause_split_ms: int = 500,
        min_duration_ms: int = 1000,
        max_duration_ms: int = 15000,
        deck_name: str | None = None,
        keep_work: bool = False,
    ) -> None: ...

    def run(
        self,
        audio: Path,
        *,
        progress: ProgressHook | None = None,
        cancel: CancellationToken | None = None,
    ) -> PipelineResult: ...
```

`Pipeline.run()` constructs a `PipelineRequest` from init args + call args,
delegates to `run_pipeline()`, and returns the `PipelineResult`.

---

### Group C: CLI (`src/audawispr/cli.py`)

**Custom TyperGroup**

```python
class _OneShotFallbackGroup(typer.core.TyperGroup):
    """Redirect unknown positional args to the hidden _oneshot command."""

    def parse_args(self, ctx: Context, args: list[str]) -> list[str]:
        known = set(self.list_commands(ctx))
        if args and args[0] not in known and not args[0].startswith("-"):
            args = ["_oneshot"] + args
        return super().parse_args(ctx, args)
```

**App and callback**

```python
app = typer.Typer(
    cls=_OneShotFallbackGroup,
    no_args_is_help=True,
    add_completion=False,
)

@app.callback()
def main(
    version: bool = typer.Option(False, "--version", help="Show version and exit."),
    verbose: bool = typer.Option(False, "--verbose", help="Print phase names to stderr."),
) -> None:
    """audawispr — audio to Anki in one shot."""
    ...
```

- Only `--version` and `--verbose` live on the callback.
- `--verbose` sets a module-level flag; `_oneshot` reads it to decide whether to
  emit progress to stderr via the progress hook.

**Hidden one-shot command**

```python
@app.command(hidden=True)
def _oneshot(
    audio: Path = typer.Argument(..., exists=True, help="Audio file to process."),
    output: Path = typer.Option(..., "--output", "-o", help="Output path (.apkg or .csv)."),
    language: str = typer.Option("fr", "--language", "-l"),
    ipa: bool = typer.Option(False, "--ipa/--no-ipa"),
    model_size: str = typer.Option("base", "--model-size"),
    device: str = typer.Option("cpu", "--device"),
    compute_type: str = typer.Option("int8", "--compute-type"),
    vad: str = typer.Option("silero", "--vad"),
    pause_split_ms: int = typer.Option(500, "--pause-split-ms"),
    min_duration_ms: int = typer.Option(1000, "--min-duration-ms"),
    max_duration_ms: int = typer.Option(15000, "--max-duration-ms"),
    deck_name: str | None = typer.Option(None, "--deck-name"),
    keep_work: bool = typer.Option(False, "--keep-work"),
) -> None:
    """Run the full pipeline in one shot."""
    ...
```

- All one-shot options live here, not on the callback.
- No `--from-manifest` on the callback.
- Existing subcommands (`doctor`, `validate`, `transcribe`, `segment`, `enrich`,
  `clip`, `export`) remain unchanged.

---

### Group D: Tests

**One-shot CLI tests** (mocked transcription backend):

- `test_one_shot_creates_apkg` — end-to-end one-shot produces a `.apkg` file
- `test_one_shot_creates_csv` — end-to-end one-shot produces CSV output
- `test_one_shot_skip_enrich_when_no_ipa` — `--no-ipa` skips enrich phase
- `test_one_shot_runs_enrich_with_ipa` — `--ipa` includes enrich phase
- `test_one_shot_work_dir_derived` — work dir is `deck/_work/` for
  `deck.apkg`
- `test_one_shot_custom_work_dir` — `--keep-work` preserves `_work/` on
  success
- `test_one_shot_progress_events` — progress hook receives events for each
  phase
- `test_one_shot_cancellation` — cancellation token stops pipeline before
  export
- `test_one_shot_unknown_command_falls_back` — `audawispr audio.mp3 -o x.apkg`
  routes to `_oneshot`
- `test_known_subcommand_not_redirected` — `audawispr doctor` and
  `audawispr transcribe` still resolve to their subcommands

**Python facade tests**:

- `test_pipeline_class_runs_full_flow` — `Pipeline(...).run(audio)` produces
  expected output
- `test_pipeline_class_skip_enrich` — `Pipeline(ipa=False).run(...)` skips
  enrichment

**Error tests**:

- Phase-specific `OneShotError` messages include the phase name, original error
  text, and an actionable suggestion (e.g. different `--model-size`).

**Regression tests**:

- All existing subcommand tests (`test_transcribe`, `test_segment`, `test_doctor`,
  etc.) still pass unchanged.

---

### Group E: Documentation

**README.md** — add a "Quickstart" section:

```markdown
## Quickstart

Turn an audio file into an Anki deck with one command:

    audawispr lesson.mp3 --output deck.apkg --language fr --ipa

Or use the Python API:

    from audawispr.pipeline import Pipeline
    Pipeline(output=Path("deck.apkg"), language="fr", ipa=True).run(Path("lesson.mp3"))
```

---

### Execution Order

```
1. Group A (core pipeline)      → uv run pytest
2. Group B (Python facade)      → uv run pytest
3. Group C (CLI)                → uv run pytest
4. Group D (tests)              → uv run pytest
5. Group E (docs)               → uv run ruff check . && uv run ruff format --check . && uv run ty check src tests && uv run pytest
6. Push, wait for CI, update phase-8.md
```

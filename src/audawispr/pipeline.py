"""Public Python facade for the audawispr pipeline."""

from __future__ import annotations

from pathlib import Path

from audawispr.core.pipeline import (
    CancellationToken,
    PipelineRequest,
    PipelineResult,
    ProgressHook,
    run_pipeline,
)


class Pipeline:
    """Narrow public API for running the full audawispr pipeline."""

    def __init__(
        self,
        output: Path,
        *,
        language: str = "fr",
        ipa: bool = False,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "int8",
        vad: bool = True,
        pause_split_ms: int = 700,
        min_duration_ms: int = 600,
        max_duration_ms: int = 7000,
        translation_provider: str = "none",
        deck_name: str | None = None,
        keep_work: bool = False,
    ) -> None:
        self._output = output
        self._language = language
        self._ipa = ipa
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._vad = vad
        self._pause_split_ms = pause_split_ms
        self._min_duration_ms = min_duration_ms
        self._max_duration_ms = max_duration_ms
        self._translation_provider = translation_provider
        self._deck_name = deck_name
        self._keep_work = keep_work

    def run(
        self,
        audio: Path,
        *,
        progress: ProgressHook | None = None,
        cancel: CancellationToken | None = None,
    ) -> PipelineResult:
        """Run the pipeline for the given audio file."""
        request = PipelineRequest(
            audio=audio,
            output=self._output,
            language=self._language,
            ipa=self._ipa,
            model_size=self._model_size,
            device=self._device,
            compute_type=self._compute_type,
            vad=self._vad,
            pause_split_ms=self._pause_split_ms,
            min_duration_ms=self._min_duration_ms,
            max_duration_ms=self._max_duration_ms,
            translation_provider=self._translation_provider,
            deck_name=self._deck_name,
            keep_work=self._keep_work,
        )
        return run_pipeline(request, progress_hook=progress, cancellation_token=cancel)

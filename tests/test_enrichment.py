from pathlib import Path
from types import SimpleNamespace

import pytest

from audawispr.core.enrichment import (
    EnrichmentOptions,
    FrenchIpaService,
    enrich_manifest,
    enrich_manifest_file,
    get_translation_provider,
)
from audawispr.core.errors import EnrichmentError
from audawispr.core.manifest import (
    SourceAudio,
    TranscriptionSettings,
    TranscriptManifest,
    TranscriptSegment,
    TranscriptWord,
    load_manifest,
)


def test_enrich_manifest_adds_french_ipa() -> None:
    enriched = enrich_manifest(_make_manifest(), EnrichmentOptions(ipa=True))

    assert enriched.segments[0].ipa is not None
    assert enriched.segments[0].ipa
    assert enriched.segments[0].ipa != enriched.segments[0].text
    assert enriched.segments[0].translation is None
    assert enriched.segments[0].translation_provider is None


def test_enrich_manifest_rejects_unsupported_ipa_language() -> None:
    manifest = _make_manifest(language="en")

    with pytest.raises(EnrichmentError, match="only supported for French"):
        enrich_manifest(manifest, EnrichmentOptions(ipa=True))


def test_enrich_manifest_keeps_translation_fields_for_none_provider() -> None:
    manifest = _make_manifest(
        translation="bonjour",
        translation_provider="fixture",
    )

    enriched = enrich_manifest(
        manifest,
        EnrichmentOptions(translation_provider="none"),
    )

    assert enriched.segments[0].translation == "bonjour"
    assert enriched.segments[0].translation_provider == "fixture"


def test_get_translation_provider_rejects_network_providers() -> None:
    with pytest.raises(EnrichmentError, match="not supported in Epic 1"):
        get_translation_provider("deepl")

    with pytest.raises(EnrichmentError, match="not supported in Epic 1"):
        get_translation_provider("openai")


def test_get_translation_provider_rejects_unknown_provider() -> None:
    with pytest.raises(EnrichmentError, match="unsupported translation provider"):
        get_translation_provider("fixture")


def test_epitran_import_failure_is_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_import_error(_name: str):
        raise ImportError("missing")

    monkeypatch.setattr("audawispr.core.enrichment.import_module", raise_import_error)

    with pytest.raises(EnrichmentError, match="Epitran is required"):
        FrenchIpaService()


def test_epitran_initialization_failure_is_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingEpitran:
        def __init__(self, _code: str) -> None:
            raise RuntimeError("bad data")

    monkeypatch.setattr(
        "audawispr.core.enrichment.import_module",
        lambda _name: SimpleNamespace(Epitran=FailingEpitran),
    )

    with pytest.raises(EnrichmentError, match="could not initialize Epitran"):
        FrenchIpaService()


def test_enrich_manifest_file_saves_valid_manifest(tmp_path: Path) -> None:
    input_path = tmp_path / "segments.json"
    output_path = tmp_path / "enriched.json"
    input_path.write_text(_make_manifest().model_dump_json(), encoding="utf-8")

    enriched = enrich_manifest_file(
        input_path,
        output_path,
        EnrichmentOptions(ipa=True),
    )
    loaded = load_manifest(output_path)

    assert enriched.segments[0].ipa
    assert loaded.segments[0].ipa == enriched.segments[0].ipa


def _make_manifest(
    language: str = "fr",
    translation: str | None = None,
    translation_provider: str | None = None,
) -> TranscriptManifest:
    return TranscriptManifest(
        language=language,
        source_audio=SourceAudio(
            file_name="lesson.mp3",
            path="/tmp/lesson.mp3",
            size_bytes=3,
            sha256="0" * 64,
            language=language,
        ),
        transcription=TranscriptionSettings(
            model_size="small",
            device="auto",
            compute_type="int8",
            vad=True,
        ),
        segments=[
            TranscriptSegment(
                id="seg-0000",
                start=0.0,
                end=0.8,
                text="Bonjour.",
                words=[
                    TranscriptWord(
                        text="Bonjour.",
                        start=0.0,
                        end=0.8,
                    )
                ],
                translation=translation,
                translation_provider=translation_provider,
            )
        ],
    )

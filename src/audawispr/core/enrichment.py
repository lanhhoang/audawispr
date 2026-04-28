"""Language-aware text enrichment for transcript manifests."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Protocol

from audawispr.core.errors import EnrichmentError
from audawispr.core.manifest import (
    TranscriptManifest,
    TranscriptSegment,
    load_manifest,
    save_manifest,
)

FRENCH_EPITRAN_CODE = "fra-Latn"
NETWORK_TRANSLATION_PROVIDERS = frozenset({"deepl", "openai"})


@dataclass(frozen=True)
class EnrichmentOptions:
    """Options for optional manifest text enrichment."""

    ipa: bool = False
    translation_provider: str = "none"


class TranslationProvider(Protocol):
    """Translation provider boundary for future online/offline providers."""

    name: str

    def enrich_segment(self, segment: TranscriptSegment) -> TranscriptSegment:
        """Return a segment with translation fields applied."""


class NoneTranslationProvider:
    """No-op translation provider used by Epic 1."""

    name = "none"

    def enrich_segment(self, segment: TranscriptSegment) -> TranscriptSegment:
        return segment


TRANSLATION_PROVIDERS: dict[str, TranslationProvider] = {
    "none": NoneTranslationProvider(),
}


def enrich_manifest(
    manifest: TranscriptManifest,
    options: EnrichmentOptions | None = None,
) -> TranscriptManifest:
    """Return a manifest with requested enrichment fields populated."""
    resolved_options = options or EnrichmentOptions()
    provider = get_translation_provider(resolved_options.translation_provider)
    ipa_service = (
        FrenchIpaService.from_language(manifest.language)
        if resolved_options.ipa
        else None
    )

    enriched_segments: list[TranscriptSegment] = []
    for segment in manifest.segments:
        enriched_segment = segment
        if ipa_service is not None:
            enriched_segment = enriched_segment.model_copy(
                update={"ipa": ipa_service.transcribe(segment.text)}
            )
        enriched_segments.append(provider.enrich_segment(enriched_segment))

    return manifest.model_copy(update={"segments": enriched_segments})


def enrich_manifest_file(
    input_path: Path,
    output_path: Path,
    options: EnrichmentOptions | None = None,
) -> TranscriptManifest:
    """Load, enrich, save, and validate a manifest file."""
    manifest = load_manifest(input_path)
    enriched_manifest = enrich_manifest(manifest, options)
    save_manifest(enriched_manifest, output_path)
    return load_manifest(output_path)


def get_translation_provider(name: str) -> TranslationProvider:
    """Resolve a translation provider without allowing network providers yet."""
    normalized_name = name.strip().lower()
    if normalized_name in NETWORK_TRANSLATION_PROVIDERS:
        msg = (
            f"translation provider is not supported in Epic 1: {normalized_name}. "
            "Use --translate none."
        )
        raise EnrichmentError(msg)

    provider = TRANSLATION_PROVIDERS.get(normalized_name)
    if provider is None:
        msg = f"unsupported translation provider: {name}"
        raise EnrichmentError(msg)
    return provider


class FrenchIpaService:
    """French IPA service backed by Epitran."""

    def __init__(self, epitran_code: str = FRENCH_EPITRAN_CODE) -> None:
        try:
            epitran_module = import_module("epitran")
        except ImportError as exc:
            msg = "Epitran is required for IPA enrichment. Run `uv sync --dev`."
            raise EnrichmentError(msg) from exc

        try:
            self._epitran = epitran_module.Epitran(epitran_code)
        except Exception as exc:
            msg = f"could not initialize Epitran for {epitran_code}: {exc}"
            raise EnrichmentError(msg) from exc

    @classmethod
    def from_language(cls, language: str) -> FrenchIpaService:
        if not _is_french_language(language):
            msg = f"IPA enrichment is only supported for French in Epic 1: {language}"
            raise EnrichmentError(msg)
        return cls()

    def transcribe(self, text: str) -> str:
        try:
            ipa = self._epitran.transliterate(text)
        except Exception as exc:
            msg = f"could not generate IPA: {exc}"
            raise EnrichmentError(msg) from exc

        normalized_ipa = ipa.strip()
        if not normalized_ipa:
            msg = "could not generate IPA: empty result"
            raise EnrichmentError(msg)
        return normalized_ipa


def _is_french_language(language: str) -> bool:
    normalized_language = language.strip().lower().replace("_", "-")
    return normalized_language == "fr" or normalized_language.startswith("fr-")

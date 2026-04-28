# Epic 1: CLI + Reusable Core

## Summary

Build a fresh Python implementation for the first usable audawispr flow: audio
file in, Anki `.apkg` deck out. The code will be structured as a reusable core
library plus a Typer CLI, with French as the default language and
language-aware interfaces for later web, desktop, and mobile wrappers.

Prior `audawispr-one` and `audawispr-two` repositories are reference material
only. Do not copy them wholesale into this repo.

## Phase Dashboard

After completing each phase, update this dashboard status, check the matching
Epic TODO item, and add the verification evidence to the completed phase file.
The CI quality workflow must stay green for every phase after Phase 1.

| # | Phase | Status |
|---|-------|--------|
| 1 | [Project Foundation + Diagnostics](phase-1.md) | ⬜ Planned |
| 2 | [Local Transcription To Manifest](phase-2.md) | ⬜ Planned |
| 3 | [Sentence Segmentation + Review TSV](phase-3.md) | ⬜ Planned |
| 4 | [IPA Enrichment + Translation Stubs](phase-4.md) | ⬜ Planned |
| 5 | [Audio Snippet Clipping](phase-5.md) | ⬜ Planned |
| 6 | [Importable Anki CSV Export](phase-6.md) | ⬜ Planned |
| 7 | [Native `.apkg` Export](phase-7.md) | ⬜ Planned |
| 8 | [One-Shot CLI + Python Facade](phase-8.md) | ⬜ Planned |

## Epic TODO

- [ ] Phase 1: Project Foundation + Diagnostics
- [ ] Phase 2: Local Transcription To Manifest
- [ ] Phase 3: Sentence Segmentation + Review TSV
- [ ] Phase 4: IPA Enrichment + Translation Stubs
- [ ] Phase 5: Audio Snippet Clipping
- [ ] Phase 6: Importable Anki CSV Export
- [ ] Phase 7: Native `.apkg` Export
- [ ] Phase 8: One-Shot CLI + Python Facade

## Public Interfaces By End Of Epic

- CLI:
  - `audawispr AUDIO --output deck.apkg --language fr --ipa`
  - `audawispr transcribe AUDIO --output out/transcript.json`
  - `audawispr validate MANIFEST`
  - `audawispr segment MANIFEST --output out/segments.json`
  - `audawispr enrich MANIFEST --ipa --output out/enriched.json`
  - `audawispr clip MANIFEST --output out/clipped.json --output-dir out/media`
  - `audawispr export MANIFEST --output deck.apkg --deck-name "My French Deck"`
  - `audawispr doctor`
- Python API:
  - `Pipeline(output=Path("deck.apkg"), language="fr").run(Path("audio.mp3"), ipa=True)`
  - lower-level phase functions importable from `audawispr.core`
- Manifest schema:
  - source audio metadata
  - transcription settings
  - segment timestamps, text, and words
  - optional `ipa`
  - optional `translation`
  - optional `audio_file`
  - schema version
- Default Anki fields:
  - `SourceText`
  - `Audio`
  - `IPA`
  - `Translation`
  - `SourceFile`
  - `TimestampRange`
  - `SegmentId`

## Assumptions

- Epic 1 is CLI + core only; web is Epic 2 and desktop is Epic 3.
- Epic 1 must run cross-platform on macOS, Linux, and Windows. Use
  cross-platform Python APIs for filesystem paths, process execution, and
  output writes.
- Python 3.11+ is acceptable.
- `faster-whisper` is the first transcription backend; the core will keep a
  backend boundary for future `whisper.cpp`.
- French defaults to language code `fr`; IPA support is French-only in Epic 1.
- First-time Whisper model download may require network, but no transcription
  API key is required.
- Translation in Epic 1 is architectural only: no network provider calls until a
  later epic explicitly adds them.
- Transcription manifests must include word timestamps, because Phase 3
  segmentation depends on them.
- CI must be set up in Phase 1 and run tests, lint, format check, and typecheck
  on Linux, macOS, and Windows. Full Whisper and FFmpeg smoke checks may stay
  mocked or optional per platform when they are too heavy for normal CI.

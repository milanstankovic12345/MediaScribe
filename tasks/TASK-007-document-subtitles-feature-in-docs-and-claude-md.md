---
id: TASK-007
title: Document subtitles feature in docs and CLAUDE.md
status: done
agent: docs-writer
skills: []
model_tier: fast
priority: p2
depends_on: ["TASK-006"]
files_allowed: ["docs/prd.md", "docs/techstack.md", "docs/blueprint.md", "docs/tasks.md", "CLAUDE.md"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "techstack.md has rows for NLLB-200 600M via CTranslate2 + sentencepiece (reason: local, free, offline, ctranslate2 already installed) and SRT/ffmpeg subtitles"
  - blueprint.md lists app/translator.py and app/subtitles.py and the subtitle data flow
  - prd.md describes the feature; tasks.md has a ticked Round 4 (subtitles) section
  - CLAUDE.md Gotchas mention NLLB Serbian is Cyrillic-only (transliterated) and the ffmpeg subtitles-filter path workaround, and Architecture mentions the new test files
max_retries: 2
attempts: 0
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Update the project docs so they describe the subtitles/translation feature as built.

## Context

Feature plan: `C:\Users\milla\.claude\plans\analyze-this-project-and-purrfect-flute.md`.
- Read the final code in `app/translator.py`, `app/subtitles.py`, `app/screens/transcribe.py` and the handoffs `reports/handoffs/TASK-002..006.md` first; document only what exists (including the pinned NLLB model repo).
- `docs/techstack.md`: Translation row (NLLB-200 600M, CTranslate2 already installed via faster-whisper, `sentencepiece`; local, free, offline; CC-BY-NC fine for personal use) and Subtitles row (SRT + ffmpeg, already required).
- `docs/blueprint.md`: module map entries and the subtitle data flow.
- `docs/prd.md`: short feature description; `docs/tasks.md`: "Round 4 (subtitles)" section with the items ticked.
- `CLAUDE.md`: Gotchas (Serbian Cyrillic-only in NLLB -> transliteration; ffmpeg subtitles-filter path workaround with cwd; translation model cache + shared `_cuda_broken`), and update the Tests bullet now that there are `tests/test_subtitles.py`, `tests/test_translator.py` and the opt-in `tests/test_e2e_subtitles.py` (`YT_TOOL_E2E=1`).
- Do not touch README.md (it has uncommitted user changes).

## Steps

1. Read the implemented code and handoffs.
2. Update each doc listed in Context.
3. Run the validation command and record the exit code in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when: the change needs files
outside `files_allowed`, an acceptance criterion is ambiguous, a dependency
is missing, or a validation command cannot run in this environment. Never
widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-007.md` (see templates/handoff.md)

---
id: TASK-025
title: Document the translated transcript document and the transcript import path
status: draft
agent: docs-writer
skills: []
model_tier: fast
priority: p3
depends_on: ["TASK-020", "TASK-021", "TASK-022", "TASK-023", "TASK-024"]
files_allowed: ["CLAUDE.md", "docs/blueprint.md", "docs/tasks.md"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -c "import pathlib,sys; c=pathlib.Path('CLAUDE.md').read_text(encoding='utf-8'); b=pathlib.Path('docs/blueprint.md').read_text(encoding='utf-8'); sys.exit(int(not all(k in c and k in b for k in ('transcript_import', 'translated_from', 'sub_doc'))))"
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "docs/blueprint.md module map lists app/transcript_import.py (parse_srt, parse_markdown, load) and the tests/ line lists tests/test_transcript_import.py"
  - "docs/blueprint.md 'Data flow (transcribe, subtitles)' describes the optional translated document (<title>.<lang>.md/.pdf, written before the SRT, exporter translated_from header line, sub_doc setting) and a new transcript-input flow (.srt/.md -> transcript_import.load -> translate -> document/SRT; no Whisper; Embed/Burn not available for transcript input; overwrite guard), exactly as built in TASK-022 and TASK-024"
  - "CLAUDE.md Architecture bullets (Subtitles, Test files) and Gotchas mention the translated document, the transcript input path, the Language-menu override and the unknown-language rule for the local engine, in the existing terse style and without emojis"
  - "docs/tasks.md gets ticked items for TASK-021 to TASK-024 (next free item numbers after the round added by TASK-020); existing items are unchanged"
  - "Only behaviour present in the code and in reports/handoffs/TASK-021.md to TASK-024.md is documented; README.md, docs/prd.md and docs/techstack.md are not touched; the validation check exits 0 and the full suite passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

Update `CLAUDE.md`, `docs/blueprint.md` and `docs/tasks.md` so they describe the translated transcript document and the SRT/Markdown transcript input exactly as built in TASK-022 to TASK-024.

## Context

- CLAUDE.md requires a `docs/blueprint.md` update when module boundaries or data flow change. TASK-023 adds a module (`app/transcript_import.py`). TASK-022 and TASK-024 change the Transcribe data flow.
- This task depends on TASK-020 because both edit the same three files. TASK-020 documents TASK-018/019 first, so this task appends to its result. If TASK-020 was dropped, remove it from `depends_on` and also cover the TASK-019 wording it would have fixed.
- Read first: `reports/handoffs/TASK-021.md` to `TASK-024.md` and the final code in `app/transcript_import.py`, `app/exporter.py` and `app/screens/transcribe.py`. If the names `transcript_import`, `translated_from` or `sub_doc` differ in the code, document the real names, adjust the validation keywords to match, and record the mismatch in the handoff.
- Style precedent: `tasks/TASK-015-document-gemini-hardening-same-language-skip-and.md` and TASK-020. `tests/` and `docs/` are gitignored by project choice; that is not something to change.
- The status stays `draft` until TASK-022 to TASK-024 are done, because their open questions decide what is documented.

## Steps

1. Read the handoffs and the final code listed above.
2. Update the `docs/blueprint.md` module map, tests line and transcribe data-flow sections.
3. Update the CLAUDE.md Architecture and Gotchas bullets.
4. Append the ticked items to `docs/tasks.md`.
5. Run every validation command and record the exit codes in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when a dependency is not done, a handoff contradicts the acceptance criteria (document what was built and list the mismatch), the change needs files outside `files_allowed`, or a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Doc changes within `files_allowed`
- `reports/handoffs/TASK-025.md` (see templates/handoff.md)

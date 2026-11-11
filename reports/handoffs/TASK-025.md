---
task: TASK-025
agent: docs-writer
model: claude-haiku-5-5
attempt: 0
status: done_with_concerns
summary: 'Updated CLAUDE.md, docs/blueprint.md and docs/tasks.md for the translated document (sub_doc, translated_from), the transcript input path (transcript_import, Translate / Subtitles only), and tasks 32 to 35 (TASK-021 to TASK-024). Both validation commands exit 0; the suite is 243 passed, 2 skipped. README.md, docs/prd.md and docs/techstack.md were not touched.'
files_modified:
  - CLAUDE.md
  - docs/blueprint.md
  - docs/tasks.md
tests:
  - cmd: |
      .venv/Scripts/python -c "import pathlib,sys; c=pathlib.Path('CLAUDE.md').read_text(encoding='utf-8'); b=pathlib.Path('docs/blueprint.md').read_text(encoding='utf-8'); sys.exit(int(not all(k in c and k in b for k in ('transcript_import', 'translated_from', 'sub_doc'))))"
    exit_code: 0
    summary: keywords transcript_import, translated_from and sub_doc found in CLAUDE.md and docs/blueprint.md
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 243 passed, 2 skipped
unresolved:
  - 'Layout of the Translated document checkbox and the Transcript file dialog filter is not visually verified; no window was launched.'
  - 'TASK-024 review CR-1 (overwrite guard runs after translation) is open in code; the docs describe the current order and do not claim otherwise.'
risks: []
decisions:
  - 'Names in the code match the task keywords (transcript_import, translated_from, sub_doc), so no keyword change was needed.'
  - 'Two stale statements were corrected because the new behaviour contradicts them: the claim that Translate / Subtitles ignores the MD/PDF checkboxes (they now pick the translated-document formats), and the playlist/local-file line that mentioned a subtitles checkbox that no longer exists.'
  - 'Transcript-input rules were written from transcribe.py _run/_validate/_clean_lang and transcript_import.load, and TASK-024 review acceptance checks; nothing was documented for unbuilt features.'
  - 'tasks.md items 32 to 35 added as Round 6 (TASK-021 to TASK-024), ticked; items 28 to 31 unchanged. TASK-025 itself is not ticked.'
  - 'CLAUDE.md and docs/ are gitignored per earlier handoffs, so the edits do not appear in git status.'
next_steps:
  - 'Code review of TASK-025 (review: code) and the orchestrator setting status through scripts/tasks.mjs.'
  - 'Code fix for TASK-024 CR-1 (move the overwrite guard before translation) is outside this task; it needs its own task if wanted.'
  - 'Manual check: Browse file with a .srt, Translate / Subtitles to German with Translated document ticked, and confirm the files and the Translated from line.'
blocker: null
---

## What changed
- docs/blueprint.md: module map gains app/transcript_import.py (parse_srt, parse_markdown, load, limits, encodings, language source) and the tests line gains test_transcript_import.py; the exporter line mentions the translated_from line. The Translate / Subtitles flow gets the translated-document bullet (checkbox, sub_doc, MD/PDF formats, written before the SRT, translated_from, Original has no line). A new transcript-input flow paragraph covers Browse file, no download/Whisper, Language menu override, the language whitelist, the unknown-language rule for the local engine, Gemini, Original as .und, title source, Embed/Burn refused, and the overwrite guard. The two-buttons paragraph and the Local file line are corrected; the UI layout line names the Translated document checkbox.
- CLAUDE.md: Core modules list adds transcript_import; the two-buttons bullet, Subtitles bullet and Test files bullet are updated; Gotchas gain a translated-document bullet and a transcript-input bullet; the test list in Gotchas includes test_transcript_import.py.
- docs/tasks.md: Round 6 (translated document, transcript input) with items 32 to 35 ticked (TASK-021 to TASK-024). Items 1 to 31 unchanged.

## Evidence
- Code read: app/transcript_import.py (parse_srt, parse_markdown, load, TRANSCRIPT_EXTS, MAX_BYTES, _decode, _split_suffix), app/exporter.py (translated_from in to_markdown, write_markdown, write_pdf), app/settings.py (sub_doc default False), app/screens/transcribe.py (Transcript filter, _validate, _args sub_doc, _run transcript branch, _clean_lang, _SAFE_LANGS, OVERWRITE_MSG, UNKNOWN_LANG_MSG), app/transcriber.py LANGUAGES (Auto = None), app/translator.py TARGETS and WHISPER_TO_NLLB.
- Handoffs read: reports/handoffs/TASK-020.md to TASK-024.md; reports/reviews/TASK-024-code.md.
- Test files checked by grep: tests/test_transcript_import.py (parse_srt, parse_markdown, load used), tests/test_transcribe_screen.py (transcript input section), tests/test_core.py (translated_from tests).
- Commands run: keyword check (exit 0); .venv/Scripts/python -m pytest -q (exit 0, 243 passed, 2 skipped); grep for stale wording (ignores / Subtitles checkbox / if ticked) and emoji check (only intended hits).

## Notes for the next session
- Open code issue from the TASK-024 review: CR-1 (the overwrite guard runs after translation, so a doomed run can spend NLLB time or Gemini quota). The docs state the current order.
- Open code issue from the TASK-024 review: CR-3 (a valid but unlisted language such as ja becomes unknown, so Original writes .und). Documented as built.
- Language whitelist lives in both transcribe.py (_SAFE_LANGS) and transcript_import (_KNOWN_CODES); the TASK-024 review CR-4 notes they can drift.
- The task file status is in_progress; the orchestrator sets it.

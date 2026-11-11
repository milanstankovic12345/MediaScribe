---
task: TASK-022
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done
summary: Added translated_from to the exporter, the sub_doc setting and a Translated document checkbox, and _run now writes <title>.<lang>.md/.pdf from the translated segments before the SRT.
files_modified:
  - app/exporter.py
  - app/settings.py
  - app/screens/transcribe.py
  - tests/test_core.py
  - tests/test_transcribe_screen.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_core.py tests/test_transcribe_screen.py -q
    exit_code: 0
    summary: 83 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 205 passed, 2 skipped
unresolved: []
risks:
  - "Open questions Q2a-Q2e were not answered by a human in the task file; implemented the recommended answers that the acceptance criteria assume."
  - "tests/ is in .gitignore, so test changes will not show in git status."
decisions:
  - "_validate checks 'not (md or pdf)' before sub_doc_var.get() so the existing out-of-scope stub in tests/test_gemini.py (no sub_doc_var) keeps passing."
next_steps:
  - "Manual check: the Translated document checkbox layout in the Translate to row is not visually verified."
blocker: null
---

## What changed
exporter: translated_from keyword on to_markdown, write_markdown, write_pdf. settings: sub_doc default False. Transcribe screen: checkbox, _args 12th element, _validate message, collect_cfg, _run sub_doc parameter writing documents at the SRT stem before write_srt.

## Evidence
Both validation commands exit 0 (see tests).

## Notes for the next session
Docs follow in TASK-025. Layout not visually verified.

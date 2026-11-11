---
task: TASK-024
agent: implementer
model: claude-sonnet-5-5
attempt: 1
status: done_with_concerns
summary: Translate / Subtitles now accepts a .srt/.md transcript via Browse (new Transcript filter), skipping download and Whisper. Language from imported files is whitelisted (SEC-1) and sr-Latn/und header values are mapped (CR-1).
files_modified:
  - app/screens/transcribe.py
  - tests/test_transcribe_screen.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py tests/test_transcript_import.py -q
    exit_code: 0
    summary: 101 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 243 passed, 2 skipped
unresolved:
  - File dialog filter not visually verified
risks:
  - Overwrite guard runs after translation (before any write), so a wasted translation is possible in that case
decisions:
  - Language from the imported file is accepted only if in LANGUAGES values or WHISPER_TO_NLLB; sr-Latn maps to sr; anything else becomes unknown (empty), so it never reaches an output path
  - Q3f-Q3j assumed per recommended answers in acceptance criteria
next_steps:
  - "Manual check: Browse file, pick a .srt, Translate / Subtitles to German, open the folder"
blocker: null
---

## What changed
app/screens/transcribe.py: Transcript filter, _validate rule, _run transcript branch, language sanitizing, overwrite guard. Tests appended to tests/test_transcribe_screen.py.
## Evidence
Both validation commands exit 0.
## Notes for the next session
Transcript with md/pdf in transcribe mode raises in _run too (defensive).

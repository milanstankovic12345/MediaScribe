---
task: TASK-010
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done
summary: Fixed _validate so Embed/Burn rejects a local audio file even when a URL is given (CR-1), and reformatted the condition (CR-5). Added Tk-free tests for _validate, _lang_code and _run (CR-2).
files_modified:
  - app/screens/transcribe.py
  - tests/test_transcribe_screen.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q
    exit_code: 0
    summary: 46 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 98 passed, 2 skipped
  - cmd: .venv/Scripts/python -c "import app.screens.transcribe"
    exit_code: 0
    summary: import ok
unresolved: []
risks:
  - tests/ is in .gitignore (CR-6) so the new test file is not tracked; needs a human decision
decisions:
  - Red step confirmed first - only the 2 URL + local mp3 EMBED/BURN cases failed before the fix
next_steps: []
blocker: null
---

## What changed
_validate drops the `not url` term and uses a parenthesized two-line condition. New tests/test_transcribe_screen.py.

## Evidence
All three validation commands exit 0.

## Notes for the next session
CR-3, CR-4, CR-7 untouched as instructed.

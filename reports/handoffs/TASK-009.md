---
task: TASK-009
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done
summary: embed() now maps 0:v, 0:a?, 1:0 so the new subtitle is s:0; burn() kills and waits ffmpeg on any exception before re-raising. Tests compare full cmd lists and cover the new cases.
files_modified:
  - app/subtitles.py
  - tests/test_subtitles.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_subtitles.py -q
    exit_code: 0
    summary: 24 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 51 passed
unresolved: []
risks:
  - Red step not run separately; tests were rewritten together with the fix.
decisions:
  - Source subtitle tracks intentionally dropped in embed (no -map 0:s?).
next_steps: []
blocker: null
---

## What changed
embed map args; burn try/except BaseException with kill+wait inside the TemporaryDirectory block; new/tightened tests (full cmd ==, creationflags, kill/wait, duration=None, N/A, OSError for both).
## Evidence
Both validation commands exit 0.
## Notes for the next session
None.

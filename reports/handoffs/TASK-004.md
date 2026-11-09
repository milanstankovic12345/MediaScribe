---
task: TASK-004
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done
summary: Added embed() and burn() plus ISO 639-2 mapping to app/subtitles.py with mocked-subprocess tests.
files_modified:
  - app/subtitles.py
  - tests/test_subtitles.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_subtitles.py -q
    exit_code: 0
    summary: 19 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 46 passed
unresolved: []
risks:
  - burn() merges ffmpeg stderr into stdout to avoid pipe deadlock; stderr tail is the last 5 non-progress lines
decisions:
  - Unknown language codes map to "und"
  - burn() copies SRT to a TemporaryDirectory as subs.srt and uses it as cwd
next_steps: []
blocker: null
---

## What changed
embed, burn, iso639_2 in app/subtitles.py; 5 new tests.
## Evidence
Both validation commands exit 0.
## Notes for the next session
Real ffmpeg not run (tests mock subprocess).

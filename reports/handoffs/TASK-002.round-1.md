---
task: TASK-002
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done
summary: Added app/subtitles.py (fmt_srt_time, to_cues, to_srt, write_srt) with tests; all pass.
files_modified:
  - app/subtitles.py
  - tests/test_subtitles.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_subtitles.py -q
    exit_code: 0
    summary: 5 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 20 passed
unresolved: []
risks:
  - write_srt uses platform newlines (CRLF on Windows); fine for SRT players.
decisions:
  - Empty-text segments yield no cues; per-segment char limit is tightened so proportional cue duration stays <= max_dur.
next_steps: []
blocker: null
---

## What changed
New pure module app/subtitles.py (imports only Segment) and tests.
## Evidence
Both validation commands exit 0.
## Notes for the next session
TASK-004 can append ffmpeg functions to the module.

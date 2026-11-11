---
task: TASK-023
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done
summary: Added app/transcript_import.py (parse_srt, parse_markdown, load, TRANSCRIPT_EXTS) with tests incl. round trips through subtitles.to_srt and exporter.to_markdown.
files_modified:
  - app/transcript_import.py
  - tests/test_transcript_import.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcript_import.py -q
    exit_code: 0
    summary: 20 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 225 passed, 2 skipped
unresolved: []
risks:
  - The 20 MB limit test monkeypatches MAX_BYTES rather than creating a 20 MB file.
decisions:
  - Assumed Q3a-Q3e recommended answers (task was in_progress).
  - Regexes use bounded character classes ([^<>]*, [^{}]*), so they run in linear time.
next_steps: []
blocker: null
---

## What changed
New module and tests as above.
## Evidence
Both validation commands exit 0.
## Notes for the next session
TASK-024 wires load() into the UI.

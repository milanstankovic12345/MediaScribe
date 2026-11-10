---
task: TASK-018
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done_with_concerns
summary: Added done_dialog module (done_payload, open_folder, DoneDialog); Audio/Video/Transcribe _run and playlist worker now return (message, path); _poll opens DoneDialog.
files_modified:
  - app/screens/done_dialog.py
  - app/screens/base.py
  - app/screens/audio.py
  - app/screens/video.py
  - app/screens/transcribe.py
  - tests/test_done_dialog.py
  - tests/test_transcribe_screen.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_done_dialog.py tests/test_transcribe_screen.py -q
    exit_code: 0
    summary: 62 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 191 passed, 2 skipped
unresolved:
  - DoneDialog is not visually verified
risks: []
decisions:
  - Warning popup called as showwarning("Open folder", msg) without parent, per acceptance text
next_steps:
  - Manual check - run a short audio download, click Open folder, confirm Explorer selects the file
blocker: null
---

## What changed
New app/screens/done_dialog.py; base._poll uses DoneDialog; _run return values changed.
## Evidence
Both validation commands exit 0.
## Notes for the next session
tests/ is gitignored by project choice.

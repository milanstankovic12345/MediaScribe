---
task: TASK-006
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done_with_concerns
summary: Added Subtitles/Translate/Video option row, validation, and subtitle pipeline to the Transcribe screen, plus settings defaults and a test.
files_modified:
  - app/screens/transcribe.py
  - app/settings.py
  - tests/test_core.py
tests:
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 52 passed, 2 skipped
  - cmd: .venv/Scripts/python -c "import app.screens.transcribe"
    exit_code: 0
    summary: import ok
unresolved:
  - UI not launched or visually verified; the pipeline (_run) has no automated test.
risks:
  - "Done message text changed from 'Transcript saved:' to 'Saved:' (lists all outputs)."
  - Invalid stored values fall back in the screen (as for model/language), not in settings.load.
decisions:
  - Subtitle pipeline runs inside the temp-dir block so the downloaded video exists for embed/burn.
next_steps: []
blocker: null
---

## What changed
settings.DEFAULTS gains subtitles, sub_target, sub_video. The Transcribe screen has a new row 2 (checkbox, target menu, video menu, both menus disabled while off). _validate, _args, collect_cfg and _run were extended. Progress split is 0.1 / 0.6 / 0.85 / 1.0. Output names are <title>.<lang>.srt, .mp4 and .burned.mp4.
## Evidence
pytest and import check both exit 0.
## Notes for the next session
Not visually verified.

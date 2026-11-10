---
task: TASK-019
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: done
summary: Transcribe screen now has Transcribe and Translate / Subtitles buttons driven by a mode; Subtitles checkbox removed; base Screen gained _build_actions/action_buttons.
files_modified:
  - app/screens/base.py
  - app/screens/transcribe.py
  - tests/test_transcribe_screen.py
  - tests/test_gemini.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py tests/test_gemini.py -q
    exit_code: 0
    summary: 105 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 196 passed, 2 skipped
unresolved: []
risks:
  - Layout not visually verified.
decisions:
  - Mode is a class default plus instance attribute set in _start_mode; _args snapshots it on the main thread.
next_steps:
  - Manually launch the app and check the two buttons side by side, disabled during a job, Audio/Video unchanged.
blocker: null
---

## What changed
base.py: _build_actions hook, action_buttons, _set_busy loops. transcribe.py: modes, two buttons, _validate/_args per mode, checkbox and _toggle_subs removed, collect_cfg drops "subtitles". _run untouched.
## Evidence
Both validation commands exit 0.
## Notes for the next session
Docs (TASK-020) still to update.

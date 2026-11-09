---
task: TASK-005
agent: test-engineer
model: claude-sonnet-5-5
attempt: 0
status: done
summary: Added opt-in e2e ffmpeg tests for embed() and burn(); skipped by default, both pass with YT_TOOL_E2E=1 on real ffmpeg.
files_modified:
  - tests/test_e2e_subtitles.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_e2e_subtitles.py -q
    exit_code: 0
    summary: 2 skipped (default, offline)
  - cmd: YT_TOOL_E2E=1 .venv/Scripts/python -m pytest tests/test_e2e_subtitles.py -q
    exit_code: 0
    summary: 2 passed in 1.2s with real ffmpeg
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 51 passed, 2 skipped
unresolved: []
risks: []
decisions:
  - No pytest.ini created; skipif needs no marker registration.
next_steps: []
blocker: null
---

## What changed
New tests/test_e2e_subtitles.py: skipif guard (YT_TOOL_E2E=1 and ffmpeg/ffprobe on PATH), lavfi 3 s clip, 2-cue non-ASCII SRT via to_cues/write_srt, embed test asserts subtitle stream, burn test asserts video present, no subtitle stream, and full decode. All under tmp_path.
## Evidence
See tests list. No production defects found.
## Notes for the next session
None.

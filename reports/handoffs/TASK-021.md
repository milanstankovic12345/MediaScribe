---
task: TASK-021
agent: implementer
model: claude-haiku-5-5
attempt: 0
status: done
summary: "Closed TASK-019 review notes CR-1, CR-2 and CR-3 on the Transcribe screen. Added busy-guard tests for _start_mode, replaced the partial _args assertions with full 11-element tuple checks in both modes, and made the Transcribe button use self.button_text. No behaviour change."
files_modified:
  - app/screens/transcribe.py
  - tests/test_transcribe_screen.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q
    exit_code: 0
    summary: "59 passed, 0 failed (57 before the new tests)"
  - cmd: .venv/Scripts/python -c "import pathlib,sys; s=pathlib.Path('app/screens/transcribe.py').read_text(encoding='utf-8'); sys.exit(int('text=self.button_text' not in s))"
    exit_code: 0
    summary: "CR-3 source check passes; the same check exited 1 before the one-line fix"
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: "198 passed, 2 skipped, 0 failed"
unresolved: []
risks:
  - "tests/ is listed in .gitignore, so tests/test_transcribe_screen.py does not appear in git status or git diff. Reviewers must read the file system copy."
decisions:
  - "CR-1 and CR-2 tests are characterization tests: they pass against the existing code. Their value was confirmed by mutation, not by a red run."
  - "Mutation M1 removed the busy guard from _start_mode: the start_mode busy test fails (1 failed, 1 passed). Reverted."
  - "Mutation M2 swapped sub_target and sub_video in _args: test_args_modes fails. Reverted."
  - "A third mutation (rewriting the model expression in an equivalent form) still passed. It is not a real behaviour change, so it is not counted."
  - "app/screens/transcribe.py was restored byte-identical after the mutations (verified with cmp)."
next_steps: []
blocker: null
---

## What changed
- app/screens/transcribe.py _build_actions: the first button now uses text=self.button_text instead of the hard-coded "Transcribe". The attribute value is unchanged, so the visible label is still "Transcribe". No other lines were touched. _run, _validate, _args and _start_mode are unchanged.
- tests/test_transcribe_screen.py:
  - test_args_modes now asserts the full 11-element _args() tuple in transcribe and subtitles mode, with distinct values: model "medium", language "de", sub_target "French", sub_video BURN, engine GEMINI, gemini_model "gm-1", key "FAKE-KEY-123" (set via monkeypatch.setenv), local file Path("clip.mp4").
  - New test_start_mode_idle_sets_mode_and_starts_once (busy=False: mode set to MODE_SUBTITLES, _start called once).
  - New test_start_mode_busy_is_ignored (busy=True: mode unchanged, _start not called).

## Evidence
- Red: before the CR-3 edit, the source check exited 1 while the screen suite was 59 passed with the new tests.
- Green: the CR-3 source check exits 0, tests/test_transcribe_screen.py 59 passed, full suite 198 passed and 2 skipped (exit 0). Exit codes were captured in a run without a pipe.
- Mutation checks: see decisions above.
- The CR-4 banner behaviour is intentionally unchanged.

## Notes for the next session
- TASK-022 and TASK-024 extend _args and the full-tuple test. Update test_args_modes when _args grows.
- tests/ is gitignored (.gitignore line 14), so this test edit is outside git tracking.

---
id: TASK-021
title: "Close TASK-019 review notes: test _start_mode, assert full _args tuple, use button_text"
status: done
agent: implementer
skills: []
model_tier: fast
priority: p3
depends_on: ["TASK-019"]
files_allowed: ["app/screens/transcribe.py", "tests/test_transcribe_screen.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -c "import pathlib,sys; s=pathlib.Path('app/screens/transcribe.py').read_text(encoding='utf-8'); sys.exit(int('text=self.button_text' not in s))"
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "CR-1: a stub-self test calls TranscribeScreen._start_mode with a recorded _start: with busy=False and MODE_SUBTITLES it sets stub.mode to MODE_SUBTITLES and calls _start exactly once; with busy=True it leaves stub.mode unchanged and does not call _start"
  - "CR-2: test_args_modes (or a replacement) asserts the complete 11-element _args() tuple in transcribe mode and in subtitles mode, with distinct values for model, language, sub_target, sub_video, engine and gemini_model so that swapping any two fields fails the test"
  - "CR-3: TranscribeScreen._build_actions creates the first button with text=self.button_text (still \"Transcribe\"), so the class attribute is no longer dead; the visible labels stay \"Transcribe\" and \"Translate / Subtitles\""
  - "No behaviour change: the bodies of _run, _validate and _args are unchanged; CR-4 (Gemini banner shows regardless of action) is intentionally left as is; the full suite passes; no new dependency"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-11
---

## Objective

Close the three low-severity findings from `reports/reviews/TASK-019-code.md` (CR-1, CR-2, CR-3) on the Transcribe screen without changing behaviour.

## Context

- Findings and recommended fixes: `reports/reviews/TASK-019-code.md` (CR-1 `_start_mode` busy guard untested, CR-2 partial `_args` assertions in `tests/test_transcribe_screen.py::test_args_modes`, CR-3 dead `button_text` at `app/screens/transcribe.py:23` vs. the hard-coded label in `_build_actions`). CR-4 is info only and is not changed.
- `_args()` currently returns `(model, md, pdf, local_file, language_code, subs, sub_target, sub_video, engine, api_key, gemini_model)`. Use `_args_stub` / `make_stub` in `tests/test_transcribe_screen.py`; give each field a distinct value (e.g. `sub_video=EMBED`, `sub_target="German"`, `cfg={"gemini_model": "m"}`, `GEMINI_API_KEY` set via monkeypatch to a dummy) so field swaps are caught.
- `_build_actions` needs a Tk root and is not unit-tested; the second validation command checks CR-3 by source text.
- This task runs before TASK-022 and TASK-024 because they edit the same two files and extend `_args`; TASK-022 then extends the full-tuple test.
- No open questions: this task can be promoted to `ready` as written.

## Steps

1. Read the review file and the current `app/screens/transcribe.py` and `tests/test_transcribe_screen.py`.
2. Add the `_start_mode` test (both busy states).
3. Replace the partial `_args` assertions with full-tuple assertions in both modes.
4. Use `text=self.button_text` in `_build_actions`.
5. Run every validation command and record exit codes and pass counts in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when the change needs files outside `files_allowed`, or a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-021.md` (see templates/handoff.md)

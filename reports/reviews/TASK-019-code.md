---
task: TASK-019
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/screens/base.py
  - app/screens/transcribe.py
  - tests/test_transcribe_screen.py
  - tests/test_gemini.py
not_checked:
  - Visual layout of the buttons (no screenshot)
  - Git history of tests/ (gitignored, read only, not diffed)
findings:
  - id: CR-1
    severity: low
    title: _start_mode busy guard and mode assignment untested
    location: app/screens/transcribe.py:100
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: test_args_modes checks only md/pdf/subs, not the other _args fields (acceptance 2)
    location: tests/test_transcribe_screen.py:148
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: TranscribeScreen.button_text is dead and duplicates the hard-coded label
    location: app/screens/transcribe.py:23
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: Gemini guidance banner shows even when only Transcribe is intended
    location: app/screens/transcribe.py:106
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - _start_mode untested (Low, confidence 90)
- **Location:** `app/screens/transcribe.py:100-104`
- **Impact:** no test pins the contract "while idle, set the mode and start once; while busy, do nothing". It is harmless today because `_run` never reads `self.mode`.
- **Reproduction:** none fails. Checked by hand on a real Tk root: `_set_busy(True)` followed by `_start_mode(MODE_SUBTITLES)` leaves the mode as transcribe.
- **Recommended fix:** a stub-self test with a recorded `_start`, for both busy=False and busy=True.

### CR-2 - Partial _args assertions (Low, confidence 85)
- **Location:** `tests/test_transcribe_screen.py:148-156`
- **Impact:** acceptance 2 requires the other fields to stay as today. Only indices 1, 2, 5 and (in another test) 3 are checked.
- **Reproduction:** swap `sub_target.get()` and `sub_video.get()` in `_args`. The suite still passes.
- **Recommended fix:** assert the full tuple in both modes.

### CR-3 - Dead button_text (Low, confidence 95)
- **Location:** `app/screens/transcribe.py:23`, `:92`
- **Impact:** maintainability only. Changing the attribute does not change the UI.
- **Reproduction:** set button_text = X. The label still reads Transcribe.
- **Recommended fix:** use `text=self.button_text` in `_build_actions`, or remove the attribute.

### CR-4 - Banner regardless of action (Info, confidence 90)
- **Location:** `app/screens/transcribe.py:106-115`
- **Impact:** the Gemini hint is visible with Gemini, a non-Original target and no key, even though Transcribe does not need Gemini. Acceptance 5 asks for this and nothing is blocked. It is a UX note only.
- **Reproduction:** choose Gemini and German with no key. The banner shows, and Transcribe still runs.
- **Recommended fix:** none for this task.

Also (info, no finding): an existing config.json keeps the stale subtitles key because `collect_cfg` no longer overwrites it. This is harmless and matches acceptance 5.

## Validation (re-run by reviewer)
- `.venv/Scripts/python -m pytest tests/test_transcribe_screen.py tests/test_gemini.py -q`: exit 0, 105 passed
- `.venv/Scripts/python -m pytest -q`: exit 0, 196 passed, 2 skipped
- Tk smoke check (stdin script, real CTk root): Transcribe shows the two buttons Transcribe and Translate / Subtitles, and `_set_busy` disables and re-enables both. `collect_cfg` has no subtitles key. The three menus are in state normal. Audio and Video each have one button with their original labels.

## Acceptance check
All 7 criteria are met. 2 has partial test coverage (CR-2). For 7, the test_gemini.py edit was confirmed by reading the file only, not diffed (tests/ is gitignored).

## Coverage statement
Inspected: the full base.py and transcribe.py; the diff against 1668a3f, with the TASK-018 hunks excluded; test_transcribe_screen.py lines 1-172; test_validate_blocks_gemini_without_key; a grep for leftover sub_var and _toggle_subs references (none). Ran both validation commands and a Tk smoke check. Not checked: the visual layout, an end-to-end click with real messageboxes, and the history of tests/.

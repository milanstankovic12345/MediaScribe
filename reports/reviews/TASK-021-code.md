---
task: TASK-021
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/screens/transcribe.py
  - app/screens/base.py
  - app/settings.py
  - tests/test_transcribe_screen.py
  - reports/reviews/TASK-019-code.md
  - reports/handoffs/TASK-021.md
not_checked:
  - Visual label of the Transcribe button (no screenshot; _build_actions needs a Tk root)
  - Git history of tests/ (gitignored, read from disk only)
findings:
  - id: CR-1
    severity: low
    title: test_args_modes uses md=True and pdf=True, so an md/pdf swap in _args is not caught
    location: tests/test_transcribe_screen.py:154
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - md/pdf swap in _args survives the full-tuple test (Low, confidence 95)

- **Location:** `tests/test_transcribe_screen.py:154` (`s.md_var, s.pdf_var = Var(True), Var(True)`). This relates to task acceptance item CR-2.
- **Impact:** The test comment says "swapping any two positions fails the test", but indices 1 and 2 hold the same value in both modes (True/True, then False/False). If `_args` swapped md and pdf, or the pdf slot read `md_var`, a user who ticked only Markdown would get a PDF. The suite would not catch it. The acceptance criterion lists only model, language, sub_target, sub_video, engine and gemini_model as needing distinct values, so it is met as written. This is a remaining test gap, not an acceptance failure.
- **Reproduction:** In memory (no file edits), I replaced `TranscribeScreen._args` with a version that has `self.pdf_var.get() and not subs, self.md_var.get() and not subs` in positions 1 and 2. `pytest tests/test_transcribe_screen.py` still reported 59 passed. A version where the pdf slot reads `md_var` also passed.
- **Recommended fix:** Use `Var(True), Var(False)` for md/pdf. Expect `("medium", True, False, ...)` in transcribe mode and `("medium", False, False, ...)` in subtitles mode. A second transcribe-mode assert with md=False, pdf=True would also pin the other direction.

## Acceptance check

- **CR-1 (start_mode):** met. `test_start_mode_idle_sets_mode_and_starts_once` and `test_start_mode_busy_is_ignored` exist. The idle test records `stub.mode` at the time `_start` is called, which also pins "mode is set before _start". The following in-memory mutations each fail exactly one of the two tests: guard removed (M6), mode assigned after `_start` (M4), mode assigned before the busy check (M5).
- **CR-2 (full _args tuple):** met as written. Both modes assert the full 11-element tuple with distinct model ("medium"), language ("German" to "de"), sub_target ("French"), sub_video (BURN), engine (Gemini), key (env "FAKE-KEY-123") and gemini_model ("gm-1"). A model/gemini_model swap (M2) fails the test, and so does a language/engine swap (M3). The md/pdf pair is the one gap (CR-1 above).
- **CR-3 (button_text):** met. `_build_actions` at `app/screens/transcribe.py:92` uses `text=self.button_text`. `button_text = "Transcribe"` is unchanged and the second button still says "Translate / Subtitles". This matches the base-class pattern at `app/screens/base.py:70`. No other code reads `button_text` in a way the change could affect.
- **No behaviour change:** met. `git diff de8a82e -- app/screens/transcribe.py` is a single-line change in `_build_actions`. `_run`, `_validate`, `_args` and `_start_mode` are byte-unchanged in the diff. The CR-4 banner logic is untouched, and no dependency was added.

## Validation (re-run by reviewer)

- `.venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q`: exit 0, 59 passed
- `.venv/Scripts/python -c "...'text=self.button_text' not in s..."`: exit 0
- `.venv/Scripts/python -m pytest -q`: exit 0, 198 passed, 2 skipped
- These results match the handoff's claims.
- Mutation checks were done in memory (the class attribute was patched before `pytest.main`, and no files were changed): M1 md/pdf swap survived. M1b pdf reads md_var survived. M2, M3, M4, M5 and M6 were killed.

## Coverage statement

**Inspected:** the full diff of `app/screens/transcribe.py` against de8a82e; the whole current `transcribe.py`; how `button_text` and `_build_actions` are used in `app/screens/base.py`; `settings.get_gemini_key` (the env var takes precedence, so the monkeypatched key is deterministic); the whole `tests/test_transcribe_screen.py`, read from disk because tests/ is gitignored; the TASK-019 review; and the TASK-021 handoff.

**Ran:** all three validation commands and the seven in-memory mutations listed above.

**Not checked:** the rendered button label, since no Tk window was opened and no screenshot was taken. The source check plus the unchanged attribute value make a regression unlikely. There is also no git history for the test file. A review with no blocking findings does not prove the code is correct.

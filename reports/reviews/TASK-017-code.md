---
task: TASK-017
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/screens/transcribe.py (full file, diff vs de306bb)
  - app/screens/base.py (callers _start, _worker, _clear; confirmed unchanged vs de306bb)
  - tests/test_transcribe_screen.py (full file)
  - tests/test_gemini.py (test_validate_blocks_gemini_without_key)
  - .venv customtkinter ctk_entry.py (bind, delete, get, placeholder handling)
  - docs/blueprint.md, docs/prd.md (local-file references)
not_checked:
  - Live Tk window behaviour of the KeyRelease and Paste bindings (no GUI run; not visually verified)
  - Mutation run of new tests against the old transcribe.py (reviewer is read-only; reasoned from code instead)
  - Full history of tests/test_gemini.py (tests/ is gitignored and untracked, so no diff exists)
findings:
  - id: CR-1
    severity: low
    title: URL-entry bindings in __init__ (KeyRelease, Paste via after_idle) are not covered by any test
    location: app/screens/transcribe.py:29
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: Cancelled-dialog case of test_pick_file_clears_url does not assert local_file and label are unchanged
    location: tests/test_transcribe_screen.py:94
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: Handoff records attempt 0 while the task has attempts 1, and its Evidence section is a single line
    location: reports/handoffs/TASK-017.md:5
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: tests/ is gitignored, so test changes (including the scope-limited test_gemini.py edit) have no diff or history
    location: .gitignore:14
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
---

## Summary

The fix is correct and minimal. `_source_file(url)` makes a non-empty URL win in both `_validate` and `_args`, so the stale `local_file` can no longer reach `_run` even if the UI bindings never fire. `_run`, `base.py` and the playlist flow are unchanged. `_pick_file` clears the URL only when a path is returned. `_on_url_change` resets the file and label only when the URL is non-empty and a file is set, and never touches the URL text. All six acceptance criteria are met.

Checked details:
- `_start` passes `self.url.get().strip()` to `_validate`, and `_args` strips the same entry, so the two calls agree on precedence (base.py:109, transcribe.py:153).
- `CTkEntry.bind(seq, cmd)` forwards to the inner `tk.Entry` with `add=True` (ctk_entry.py:290-294), so the internal CTk bindings are kept. `CTkEntry.get()` returns "" while the placeholder is active, so the placeholder never counts as a URL.
- Widget-level `<<Paste>>` bindings run before the Entry class binding inserts the text, so deferring the check with `after_idle` is correct. The lambda returns an `after#N` id, not "break", so paste still works. Ctrl+V also produces a KeyRelease after the insert.
- The KeyRelease from pressing Enter to close the file dialog is harmless: `_pick_file` has already cleared the URL synchronously, so the handler sees an empty URL.
- The new tests would fail on the old code. With the old code, the URL-wins `_validate` returned EMBED_MSG, `_args[3]` was `local_file`, `_source_file` and `_on_url_change` did not exist, and `_pick_file` did not clear the URL. I reasoned this from the code; I did not run it.
- In `test_gemini.py`, the visible change is only the `_source_file` line at line 233, as the widened scope allows.
- No new dependency. No docs change is needed: blueprint describes data flow, not input precedence.

## Findings

### CR-1 — URL-entry bindings are untested (Low, confidence 90)

- **Location:** `app/screens/transcribe.py:29-30`
- **Impact:** If someone removes or misnames the binding, for example binding `<<Paste>>` without `after_idle`, no test fails. In that case the handler checks the pre-paste text and the label keeps showing the old file until the next keystroke. Correctness is not affected, because `_validate` and `_args` use `_source_file`, but the UI state sync would silently regress.
- **Reproduction:** Delete line 30 and run `pytest tests/test_transcribe_screen.py`. All tests still pass.
- **Recommended fix (optional):** Add a stub test that calls `TranscribeScreen.__init__` with `Screen.__init__` monkeypatched to set `self.url` to a fake that records `bind` calls, and `self.after_idle` recording its argument. Then assert that both sequences are bound and that the Paste callback schedules `_on_url_change`.

### CR-2 — Cancelled-dialog branch is under-asserted (Low, confidence 90)

- **Location:** `tests/test_transcribe_screen.py:94-97`
- **Impact:** The acceptance criterion says "cancelled dialog changes nothing". The test checks only that the URL is unchanged. A regression that resets `local_file` or the label on cancel would pass.
- **Reproduction:** Change `_pick_file` to set `self.local_file = None` on an empty return. `test_pick_file_clears_url` still passes.
- **Recommended fix:** After the cancelled call, also assert `stub.local_file == Path("C:/m/a.mp3")` and that `stub.text` is still the "Local file: a.mp3" label.

### CR-3 — Handoff metadata and evidence are thin (Info, confidence 95)

- **Location:** `reports/handoffs/TASK-017.md:5`
- **Impact:** The handoff says `attempt: 0`, but the task frontmatter has `attempts: 1`. "What changed" just says "See summary", and Evidence is one line. Both validation results matched my reruns, so this is bookkeeping only.
- **Recommended fix:** The orchestrator or implementer should set `attempt` from the task file in future handoffs.

### CR-4 — Tests are untracked (Info, pre-existing, confidence 95)

- **Location:** `.gitignore:14` (`tests/`)
- **Impact:** None of the test files are in git (`git ls-files tests` is empty). Test changes cannot be reviewed as a diff, and the scope limit on `tests/test_gemini.py` can be checked only by reading the current file. This is pre-existing and outside the task.
- **Recommended fix:** A separate task to stop ignoring `tests/`, if that is intended.

## Validation re-run (by reviewer)

- `.venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q`: exit 0, 52 passed. Matches the handoff.
- `.venv/Scripts/python -m pytest -q`: exit 0, 181 passed, 2 skipped. Matches the handoff.
- `git diff --quiet de306bb -- app/screens/base.py`: no change.

## Coverage statement

What I inspected:
- The full `app/screens/transcribe.py` and its diff against de306bb.
- In `app/screens/base.py`: `_start`, `_worker`, the playlist path and `_clear`. I confirmed the file is unchanged.
- All of `tests/test_transcribe_screen.py`.
- The `_validate` stub test in `tests/test_gemini.py`.
- In the installed CustomTkinter `CTkEntry`: `bind`, `delete`, `get` and the placeholder logic.
- The docs that mention local files.

What I ran: both validation commands.

What I did not check:
- Real Tk event delivery for KeyRelease and Paste in a running window (not visually verified).
- A mutation run of the new tests against the old code. The reviewer sandbox is read-only, so I reasoned about it from the code.
- Earlier contents of the untracked test files.

Finding no defects does not prove the code is correct.

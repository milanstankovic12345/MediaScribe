---
task: TASK-008
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/gemini.py
  - app/translator.py
  - app/settings.py
  - app/ui.py
  - app/screens/settings_screen.py
  - app/screens/transcribe.py
  - app/screens/base.py
  - tests/test_gemini.py
  - tests/test_core.py
  - docs/techstack.md
  - docs/blueprint.md
  - docs/tasks.md
  - CLAUDE.md
not_checked:
  - Real Gemini API calls; model gemini-3.5-flash-lite free-tier status not independently verified
  - Visual layout and link opening (no screenshot)
findings:
  - id: CR-1
    severity: medium
    title: Blocked/empty Gemini response aborts translation instead of retry then NLLB fallback
    location: app/gemini.py:89-93,135-144
    confidence: 92
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: HTTP 5xx (503 overloaded) not retried and aborts the run
    location: app/gemini.py:81
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: Changing Translate-to target does not refresh Gemini guidance
    location: app/screens/transcribe.py:61
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: low
    title: Test connection checks entry key, not the env key runs use
    location: app/screens/settings_screen.py:103
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-5
    severity: low
    title: No test for TranscribeScreen._run Gemini branch wiring
    location: app/screens/transcribe.py:194-196
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-6
    severity: info
    title: Gemini path skips same-language shortcut; fallback fails for non-NLLB sources
    location: app/translator.py:170-175
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - Blocked/empty response aborts translation (Medium, confidence 92)
- **Location:** `app/gemini.py:89-93`, `135-144`
- **Impact:** A 200 response with no text (`promptFeedback.blockReason`, or `finishReason` SAFETY/RECITATION with no parts, e.g. lyrics) makes `_text_of` raise `GeminiError`. `_translate_chunk` only catches ValueError/KeyError/TypeError, so the retry and the NLLB fallback are skipped and the whole subtitle step fails. This goes against the acceptance criterion "missing/extra ids retried once, then local NLLB". An empty JSON array already falls back, so this case should too.
- **Reproduction (run):** fake urlopen returning `{"candidates":[{"finishReason":"RECITATION"}]}`. Result: `GeminiError: Gemini returned no text`, 1 request, fallback not called.
- **Fix:** in `_translate_chunk`, treat a GeminiError from `_text_of` (not from `_post`) as a mismatch and return None. Add a test.

### CR-2 - 5xx not retried (Low, confidence 90)
- **Location:** `app/gemini.py:81`
- **Impact:** A 503 "model overloaded" (common on the free tier) fails the whole run on the first try, with no fallback. The task asked only for 429 retries.
- **Reproduction (run):** HTTPError(503) gives `Gemini request failed (HTTP 503)` after 1 request.
- **Fix:** back off on 500/503 like 429, or fall back to NLLB per chunk on kind "other".

### CR-3 - Guidance not refreshed on target change (Low, confidence 95)
- **Location:** `app/screens/transcribe.py:61`. `sub_target` has no `command`.
- **Impact:** With Subtitles on, Gemini selected, no key and target Original, switching the target to German leaves the guidance hidden. Start is still blocked by `_validate`. The reverse also happens: switching back to Original leaves stale guidance visible.
- **Reproduction (headless Tk, run):** `winfo_ismapped()` is False while `_gemini_missing()` is True.
- **Fix:** `command=lambda _v: self._update_guidance()` on `sub_target`.

### CR-4 - Test connection uses the wrong key when the env var is set (Low, confidence 85)
- **Location:** `app/screens/settings_screen.py:103`
- **Impact:** The entry key is tested first, but runs use `GEMINI_API_KEY`. The test can report Connected for a key that is never used.
- **Fix:** test `settings.get_gemini_key(self.cfg)` when the env var is set.

### CR-5 - `_run` Gemini branch untested (Low, confidence 90)
- **Location:** `app/screens/transcribe.py:137-141`, `194-196`
- **Impact:** The `_args` order, the `_run` signature and the positional call to `translator.translate` are correct by inspection only. A reorder could route the key into the log callback, and no test would catch it.
- **Fix:** add a stub-self test in `tests/test_transcribe_screen.py` that asserts the key and model reach `translate` and that no `_say` message contains the key.

### CR-6 - Dispatch notes (Info, confidence 80)
- **Location:** `app/translator.py:170-175`
- **Impact:** Gemini is called even when source and target are the same language, which wastes quota. For sources NLLB lacks (e.g. ja), a twice-failed chunk falls back to NLLB, which raises ValueError and aborts the run.
- **Fix (optional):** short-circuit same-language cases. For unsupported sources, keep the original text in the fallback and log it.

## Acceptance check
All 10 criteria are met by code reading and tests. Exceptions: CR-1 (a blocked response gets no fallback) and CR-3 (guidance refresh). The key appears only in the `x-goog-api-key` header. Errors are fixed strings raised `from None`, and `base._worker`/`_poll` show only those. All screens share the `cfg` dict, so a saved key is visible without restart. No new dependency. All four docs updated.

## Validation re-run
- `pytest tests/test_gemini.py -q`: exit 0, 24 passed
- `pytest -q`: exit 0, 123 passed, 2 skipped (matches the handoff)
- `python -c "import app.ui, app.screens.settings_screen"`: exit 0
- Inline repros for CR-1 and CR-2 (faked urlopen), and a headless Tk smoke for CR-3

## Coverage statement
Read: all six app files in scope, `screens/base.py` (to check for key leaks into logs and popups), `tests/test_gemini.py`, the settings test in `test_core.py`, and the Gemini sections of the four docs. Not checked: real API responses, whether the model exists, visual layout, link opening, and security (a separate review). No findings would not prove the code correct.

---
task: TASK-012
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/gemini.py (full file, diff vs fb6fe58)
  - tests/test_gemini.py (full file; working tree, gitignored so not in git diff)
  - app/screens/settings_screen.py:110 and app/screens/transcribe.py:142,197 (callers passing gemini_model)
  - .gitignore
not_checked:
  - Real Gemini API behaviour (no network by design)
  - Python versions other than 3.11.15 for RecursionError behaviour of json.loads
  - Security review (separate security review is required for this task)
findings:
  - id: CR-1
    severity: info
    title: tests/ is gitignored, so the TASK-012 test changes are not version-controlled or visible in the review diff
    location: .gitignore:14
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
---

## Summary

The change does what the task asks. `_post` now uses `isinstance(model, str)` before the regex. 502 and 504 join the retry set. `RecursionError` is caught at both `json.loads` sites: the outer body maps to the "unreadable response" GeminiError, and an inner-text error returns `None` from `_translate_chunk`. The four stale strings are updated. I checked every acceptance criterion against the code and the tests:

- CR-1 (model): `tests/test_gemini.py:285-294` adds `2` and `["x"]` alongside the existing invalid, valid and None cases, and asserts the URL for both `check_key` and `translate_segments`. The callers (`settings_screen.py:110` and `transcribe.py:142`) pass `cfg.get("gemini_model") or None`, so a truthy non-str value from config.json reaches `_post`. It is now replaced by `MODEL` and no longer raises a TypeError.
- CR-3 (502/504): `gemini.py:89` handles them. The last-try mapping is unchanged: 429 gives `rate_limited` and any 5xx gives `other` with "Gemini request failed (HTTP <code>)". `test_5xx_retried_then_ok` is parametrized over [500, 502, 503, 504] with `sleeps == [5]`. `test_three_504s_give_up` checks the exact message, 3 requests, sleeps [5, 15] and that the key is absent.
- SEC-5 inner: `test_deeply_nested_inner_text_is_mismatch` checks 2 requests and that the fallback text is used.
- SEC-5 outer: `test_deeply_nested_outer_body_is_unreadable` checks kind `other`, the exact message, 1 request and that the key is absent.
- CR-2: `gemini.py:24`, `gemini.py:75`, `tests/test_gemini.py:1` and `tests/test_gemini.py:43` are updated.
- No new imports or dependencies, and no UI code in `app/gemini.py`.

## Validation (re-run by reviewer)

| Command | Exit | Result |
|---|---|---|
| `.venv/Scripts/python -m pytest tests/test_gemini.py -q` | 0 | 48 passed |
| `.venv/Scripts/python -m pytest -q` | 0 | 148 passed, 2 skipped |

These match the handoff counts.

Red check: the handoff says no red run was recorded, so I ran one. I loaded the base `fb6fe58:app/gemini.py` into the `app.gemini` module in memory (exec into its namespace; no files written) and ran the current `tests/test_gemini.py` against it. 7 tests failed and 41 passed. The failures were exactly the new cases: `test_model_name_validated[2]`, `test_model_name_validated[["x"]]`, `test_5xx_retried_then_ok[502]`, `[504]`, `test_three_504s_give_up`, `test_deeply_nested_inner_text_is_mismatch` (RecursionError) and `test_deeply_nested_outer_body_is_unreadable` (RecursionError). So the new tests do catch the defects they target, and on Python 3.11.15 `json.loads` does raise RecursionError for 100000-deep input.

## Findings

### CR-1 — tests/ is gitignored, so the TASK-012 test changes are not version-controlled (Info, confidence 95)

- **Location:** `.gitignore:14` (`tests/`), affecting `tests/test_gemini.py`
- **Impact:** The task's diff command `git diff fb6fe58 -- app/gemini.py tests/test_gemini.py` shows only `app/gemini.py`. The new and parametrized tests exist only on the local disk, so a fresh clone gets the hardened code without the regression tests that cover it. This is a deliberate, pre-existing project choice ("Dev-only, kept locally"), not something this change introduced, so it does not count against the task.
- **Reproduction:** `git check-ignore -v tests/test_gemini.py` prints `.gitignore:14:tests/`. `git diff fb6fe58 --stat -- app/gemini.py tests/test_gemini.py` lists only `app/gemini.py`.
- **Recommended fix:** None for this task. If the owner wants regression protection in version control, un-ignore `tests/` in a separate task. Otherwise, reviewers should keep reading the working-tree test file directly, as done here.

## Questions (below the reporting threshold)

- None.

## Coverage statement

What I inspected:
- The full `app/gemini.py` and its diff against fb6fe58.
- The full working-tree `tests/test_gemini.py`.
- The callers that pass `gemini_model`, found by grep.
- `.gitignore`.

What I ran:
- Both validation commands, with the real exit codes.
- The in-memory red check of the new tests against the base implementation.

Edge cases I reasoned about:
- `""`, `True` and str subclasses as model. All are handled: the regex needs at least one character, and `bool` is not a `str`.
- `retryDelay` on 502/504. This uses the shared `_retry_delay` path but has no dedicated test, and the acceptance criteria do not require one.
- A RecursionError raised inside the `with _open(...)` block. The context manager exits cleanly.

What I did not check:
- Real network behaviour.
- RecursionError behaviour on Python versions other than 3.11.15.
- Security concerns beyond key absence in error messages, which the separate security review covers.

No findings does not prove the code is correct.

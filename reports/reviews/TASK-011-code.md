---
task: TASK-011
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/gemini.py
  - app/screens/settings_screen.py
  - app/screens/transcribe.py
  - app/settings.py (get_gemini_key, load)
  - app/translator.py (translate dispatcher)
  - tests/test_gemini.py
  - tests/test_transcribe_screen.py
  - reports/reviews/TASK-008-code.md
  - reports/reviews/TASK-008-security.md
  - reports/handoffs/TASK-011.md
not_checked:
  - Live Gemini API (no key, no network by rule)
  - Visual appearance of the guidance row (functional Tk check only, window withdrawn)
  - Security review (separate reviewer)
findings:
  - id: CR-1
    severity: low
    title: Non-string gemini_model escapes the SEC-4 check as a raw TypeError
    location: app/gemini.py:76
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: Stale comments and docstrings still say only 429 is retried and urlopen is faked
    location: app/gemini.py:24,75; tests/test_gemini.py:1,43
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: 502 and 504 are not retried (only 500/503 per the task)
    location: app/gemini.py:89
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - Non-string gemini_model escapes the SEC-4 check as a raw TypeError (Low, confidence 95)

- **Location:** `app/gemini.py:76` (`if not model or not _MODEL_RE.fullmatch(model)`)
- **Acceptance criterion:** SEC-4
- **Impact:** `gemini_model` comes from hand-edited `config.json`, where any JSON type is possible. A truthy non-string, such as `2` or `["x"]`, reaches `re.fullmatch` and raises `TypeError: expected string or bytes-like object, got 'int'`. It is not replaced by `MODEL`. The translation run then fails with that raw message, and Settings shows "Error: expected string...". No key leaks. SEC-4 asks that anything that does not fully match the pattern falls back to `MODEL`, and this case does not.
- **Reproduction (run):** `gemini._post({}, "FAKE-KEY-123", 2)` raises TypeError. The same happens for `["x"]`.
- **Recommended fix:** `if not isinstance(model, str) or not _MODEL_RE.fullmatch(model): model = MODEL`. Add `2` to the `test_model_name_validated` parametrize list.

### CR-2 - Stale comments and docstrings (Low, confidence 95)

- **Location:** `app/gemini.py:24` (BACKOFF comment says "after HTTP 429"), `app/gemini.py:75` (`_post` docstring says "retries HTTP 429"), `tests/test_gemini.py:1` and `:43` ("urlopen is faked" / "served by urlopen"). Requests now go through `gemini._open`.
- **Impact:** A maintainer reading these would miss the 500/503 retry, or would patch `urlopen` in a new test and accidentally reach the network. `CLAUDE.md:37` also says "Tests mock `urlopen`". That file is outside this task's scope, so it is reported for the orchestrator.
- **Recommended fix:** update the four in-scope strings to "429/500/503" and "`gemini._open` is faked". Route the CLAUDE.md line (and the optional redirect/5xx doc line from the handoff) to a docs task.

### CR-3 - 502/504 not retried (Info, confidence 80)

- **Location:** `app/gemini.py:89`
- **Acceptance criterion:** CR-2 (5xx)
- **Impact:** A 504 (DEADLINE_EXCEEDED) or a 502 from Google fails the run on the first try. This matches the task, which names only 500/503, so it is not a defect against the acceptance criteria.
- **Suggestion:** consider `e.code in (429, 500, 502, 503, 504)` in a later task.

## Acceptance check

- **CR-1 (blocked reply):** met. `_post` sits outside the `try`. A `GeminiError` from `_text_of` returns None. Both shapes are requested exactly twice, then the fallback runs and logs "using local translation for it". Without a fallback, `GeminiError` kind other is raised. Tests cover both shapes and both paths.
- **SEC-2:** met. `_opener = build_opener(_NoRedirect)`, and `redirect_request` returns None. I checked it against a real local HTTP server (stdin probe, nothing written): a POST that got a 302 made exactly one request with no follow-up GET, and raised `GeminiError other "Gemini request failed (HTTP 302)"` with no key in it. The tests cover the handler and the 3xx mapping.
- **SEC-3:** met. `type(x["i"]) is int` rejects Infinity, NaN, floats, bools and strings, and the except also catches ArithmeticError. Infinity is tested and falls back after one retry. The existing parametrized bad-id tests still pass.
- **SEC-4:** met for strings: invalid, valid and None are tested for both `check_key` and `translate_segments`. A non-string is not handled (CR-1).
- **CR-2 (5xx):** met. Sleeps are `[5, 15]`, three 500s give up with kind other, and the error is keyless. Against the real local server, three 503s with `retryDelay: 2s` slept 2.0 twice, made 3 requests, then raised "HTTP 503".
- **Existing tests:** still pass. The key appears only in the header (request-shape test).
- **CR-3 (target menu):** met. `command=lambda _v: self._update_guidance()`. A functional Tk check with the window withdrawn ran the menu command. With no key and Gemini selected, German puts the guidance on the grid and Original takes it off. Not visually verified.
- **CR-4:** met. The env key wins over the entry and saved key, and the status reads "Testing GEMINI_API_KEY from environment..." without the key. Without the env var it uses the entry key, else the saved key. Thread is monkeypatched in the tests.
- **CR-5:** met. `translate` receives (German, GEMINI_ENGINE, key, "m"), `translate_segments` is not called, and neither `said` nor the Saved string contains the key.
- **No new dependency; no network in tests:** met. `net` patches `gemini._open`, and `urlopen` is unused in `app/`.

## Validation re-run

- `.venv/Scripts/python -m pytest tests/test_gemini.py -q`: exit 0, 41 passed (matches the handoff)
- `.venv/Scripts/python -m pytest -q`: exit 0, 141 passed, 2 skipped (matches the handoff)
- Stdin probe against a local `http.server` for a real 302 refusal and real 503 retries; `_post` with model `2` and `["x"]`
- Functional Tk check of the `sub_target` command (window withdrawn, built from a defaults cfg, so the user config was not touched)

## Coverage statement

Read all of `app/gemini.py`, `app/screens/settings_screen.py`, the `transcribe.py` diff since 5cb55fb, `settings.get_gemini_key`/`load`, the `translator.translate` dispatcher, all of `tests/test_gemini.py`, and the stub, fixture and Gemini test in `tests/test_transcribe_screen.py`. I reasoned through whether each new test fails without its fix. All do except the 3xx-mapping test, which would pass on the old generic HTTPError path, but the handler test covers the refusal. I could not use git stash because the files are untracked and this agent is read-only.

Note: `tests/` is in `.gitignore` ("Dev-only, kept locally", commit eab24b9). The new tests are therefore not version-controlled. That was a deliberate project choice, so it is recorded here and not as a finding.

Not checked: live Gemini responses, visual layout, and security beyond the key-leak checks above (a separate review). Finding no further issues does not prove the code correct.

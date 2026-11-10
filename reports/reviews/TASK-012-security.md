---
task: TASK-012
kind: security
reviewer: security-reviewer
model: claude-opus-5-5
round: 1
verdict: approve
scope_checked:
  - app/gemini.py (full file, diff vs fb6fe58)
  - tests/test_gemini.py (full new/changed tests; file is gitignored, so not in git diff)
  - app/screens/transcribe.py:142,164,197 (gemini_model source)
  - app/screens/settings_screen.py:110-115 (check_key caller)
  - app/translator.py:173 (translate_segments caller)
not_checked:
  - app/settings.py key storage (TASK-014 scope)
  - UI error display paths beyond confirming GeminiError messages are key-free
  - dependency/supply-chain (no dependency change)
findings:
  - id: SEC-1
    severity: info
    title: Response body read without a size cap (pre-existing, unchanged by this task)
    location: app/gemini.py:85
    confidence: 70
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-2
    severity: info
    title: Regression tests for these fixes are not version-controlled (tests/ is gitignored)
    location: .gitignore (tests/)
    confidence: 95
    status: open
    verified: true
    acceptance_ref: null
---

## Summary

Verdict approve. The three security-relevant changes (non-str model validation, 502/504 retries,
RecursionError handling at both json.loads sites) are correct, bounded and key-free. I verified each
fix by running old and new code in memory against the same fake responses. No Critical, High, Medium
or Low findings.

## Verification (commands run this session)

- `.venv/Scripts/python -m pytest tests/test_gemini.py -q`: exit 0, 48 passed (Python 3.11.15).
- `.venv/Scripts/python -m pytest -q`: exit 0, 148 passed, 2 skipped.
- In-memory old (fb6fe58) vs new comparison with a fake `_open`, no network, no files written:
  - model=2: old raised TypeError; new uses gemini.MODEL.
  - 100000-deep outer body: old let RecursionError escape `check_key`; new raises GeminiError kind
    other "Gemini returned an unreadable response" after 1 request.
  - 100000-deep inner text: old let RecursionError escape `translate_segments`; new falls back
    (`["local"]`).
  - 504 x3: old made 1 request; new makes 3 requests, then raises "Gemini request failed (HTTP 504)".
  So the new tests fail on the old code and guard the fixes. The implementer's handoff did not record
  a red run.
- Confirmed RecursionError is not a ValueError or OSError subclass, so the separate catch is needed
  and the `except` order (HTTPError, OSError, ValueError/RecursionError) is correct.

## Analysis

- **Model name to URL path (CWE-20 / CWE-74):** `isinstance(model, str)` plus `_MODEL_RE.fullmatch`
  (`[A-Za-z0-9.\-]+`) blocks `/`, `?`, `#`, `%`, `:`, whitespace and trailing newlines. The values `.`
  and `..` pass the regex, but the path segment becomes `..:generateContent`. That is not a dot-segment,
  so the request cannot leave `/v1beta/models/`. The host is fixed. Source is the local config only.
- **Retry amplification (CWE-400):** each `_post` is still capped at MAX_TRIES=3 and each sleep at
  120 s (`_retry_delay`). A 5xx on the last try raises from `_post`, outside `_translate_chunk`'s
  try, so it does not trigger the mismatch retry. Worst case per chunk is 3 requests and about 240 s.
- **Deep nesting (CWE-674):** both parse sites now catch it. Python's C scanner raises it without
  exhausting the interpreter stack, so recovery in the `except` is safe. The outer case does not retry.
- **Secret exposure (CWE-209 / CWE-532):** new and changed messages contain only the HTTP status
  code or fixed text, and all are raised `from None`. The 5xx body is used only by `_retry_delay`. The
  key stays only in the `x-goog-api-key` header, and the redirect refusal is unchanged.

## Findings

### SEC-1: Response body read without a size cap (Info, confidence 70)

- **Category:** CWE-400 / CWE-770
- **Location:** `app/gemini.py:85` (`r.read()`), and `e.read()` at `:95`
- **Exploit scenario:** this needs a hostile or compromised endpoint behind valid Google TLS, which is
  not realistic. A very large body would be held in memory in full. This is pre-existing and not
  introduced by TASK-012.
- **Fix (optional):** `r.read(MAX_BODY + 1)` with a limit of a few MB, mapped to "unreadable response".
- **Test:** serve a fake response larger than the limit and expect GeminiError kind other after 1 request.

### SEC-2: Regression tests not version-controlled (Info, confidence 95)

- **Category:** process (OWASP A08-adjacent: integrity of the verification suite)
- **Location:** `.gitignore` lists `tests/`
- **Impact:** the tests guarding the TASK-011/012 hardening (key-in-header only, redirect refusal,
  model validation, recursion handling) exist only in this working copy. The brief's
  `git diff ... -- tests/test_gemini.py` shows nothing. A clean checkout would have no regression
  guard. This looks like a deliberate project choice ("Dev-only, kept locally"), so it is for the
  orchestrator or human to decide.
- **Fix:** none required by this task. Optionally track `tests/` or back them up elsewhere.

## Coverage statement

Reviewed: every changed line of `app/gemini.py`, the whole module (to trace the data flow from the
config model name and the HTTP response to the URL, sleep and parsers), all new and changed tests in
`tests/test_gemini.py`, and the three call sites that pass `gemini_model` and the key. References:
the OWASP Top 10 baseline, input validation (the model name in the URL, untrusted JSON) and secrets
(key in errors and logs). Tools: pytest (both validation commands) and an in-memory comparison of old
and new code. Not reviewed: key storage at rest (TASK-014), UI rendering of errors beyond the message
text, and the supply chain (no dependency change). No live requests to Gemini were made. This review
covers the checked paths only and is not a statement that the application is secure.

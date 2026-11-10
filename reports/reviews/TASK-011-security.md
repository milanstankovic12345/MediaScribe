---
task: TASK-011
kind: security
reviewer: security-reviewer
model: claude-opus-5-5
round: 1
verdict: approve
scope_checked:
  - app/gemini.py
  - app/screens/settings_screen.py
  - app/screens/transcribe.py
  - app/translator.py
  - tests/test_gemini.py
  - tests/test_transcribe_screen.py
not_checked:
  - Live Gemini API (external, no key)
  - UI rendering of CR-3 (no display)
  - SEC-1 plaintext key (deferred by the task)
  - CR-6 translator fallback logic
  - Dependencies (none added)
findings:
  - id: SEC-5
    severity: info
    title: RecursionError from deeply nested JSON escapes parsing and skips retry and fallback
    location: app/gemini.py:85,103,155,164
    confidence: 90
    status: open
    verified: true
    acceptance_ref: null
  - id: SEC-2
    severity: low
    title: (TASK-008) redirects forwarded the API key header - fixed
    location: app/gemini.py:48-60
    confidence: 95
    status: fixed
    verified: true
    acceptance_ref: null
  - id: SEC-3
    severity: info
    title: (TASK-008) OverflowError on Infinity id - fixed
    location: app/gemini.py:156,164
    confidence: 95
    status: fixed
    verified: true
    acceptance_ref: null
  - id: SEC-4
    severity: info
    title: (TASK-008) unvalidated model name in URL - fixed
    location: app/gemini.py:56,76-78
    confidence: 90
    status: fixed
    verified: true
    acceptance_ref: null
---

## Findings

| id | severity | category | location | confidence | status |
|---|---|---|---|---|---|
| SEC-5 | info | CWE-674, CWE-20 | app/gemini.py:85,103,155,164 | 90 | open |
| SEC-2 | low | CWE-200, A05 | app/gemini.py:48-60 | 95 | fixed, verified |
| SEC-3 | info | CWE-20 | app/gemini.py:156,164 | 95 | fixed, verified |
| SEC-4 | info | CWE-20 | app/gemini.py:56,76-78 | 90 | fixed, verified |

### SEC-5 - RecursionError from deeply nested JSON (Info, confidence 90)

- **Location:** gemini.py:85 (outer body, line 103 catches only ValueError) and gemini.py:155 (reply text, line 164 lacks RecursionError).
- **Evidence:** reproduced here with a faked _open. A reply text nested 100000 arrays deep made translate_segments raise RecursionError, with no retry and no fallback. Same for a deeply nested outer body. No key in the message.
- **Exploit scenario:** needs Google (verified TLS, responseSchema) to emit such a reply, at most via prompt injection from a hostile transcript. Impact: one job fails instead of falling back to NLLB. No key leak.
- **Fix:** add RecursionError to the except at line 164, and catch (ValueError, RecursionError) at line 103.
- **Test:** deeply nested text leads to fallback after 2 requests. A deeply nested body raises GeminiError kind other without the key.

### SEC-2 - fixed, verified

The handlers of _opener include _NoRedirect and no stock HTTPRedirectHandler. HTTPSHandler is the default (TLS unchanged). Loopback probe on 127.0.0.1: for 301, 302, 303, 307 and 308, check_key sent one request, never hit the Location target, and raised GeminiError kind other "Gemini request failed (HTTP 3xx)" without the key. Control: stock urlopen followed the 302 and sent x-goog-api-key to the target.

### SEC-3 - fixed, verified

Probed Infinity, -Infinity, NaN, true, 0.0, a 5001-digit int, an object instead of an array, a non-string t, non-string text, and an outer list or string body. All fell back after one retry. Invalid UTF-8 gave a keyless "unreadable response".

### SEC-4 - fixed, verified

fullmatch in _post covers check_key and translate_segments. A trailing newline and non-ASCII are rejected. Dot-only names give the segment "..:generateContent", which is not a dot segment, so no traversal. The host is fixed.

## Verified claims

- CR-1: _post is outside the try, so key, network and rate errors still propagate.
- CR-2: 500 and 503 use the 429 backoff, at most 3 requests, retryDelay capped at 120 s, and a keyless final error.
- CR-4: the env key is tested first, and the status names the source, never the value.
- CR-5: the key reaches only translator.translate, then gemini, then the header. It is not in _say messages or in the result.
- No AIza match in app/ or tests/.
- pytest tests/test_gemini.py: 41 passed. Full suite: 141 passed, 2 skipped (run here).

## Coverage statement

Reviewed: all of gemini.py, settings_screen._test and its worker, the TASK-011 diff of transcribe.py, the translator.translate dispatcher, and the new tests. References: OWASP baseline, secrets, input validation. Tools: pytest, a loopback HTTP probe (127.0.0.1 only), in-memory parsing probes. Python 3.11.15. Not reviewed: the live API, UI rendering, SEC-1, CR-6, docs, deps. This review does not show that the feature is secure. It records only what was checked.

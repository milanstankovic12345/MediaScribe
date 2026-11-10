---
id: TASK-012
title: Handle Gemini model-name, 502/504 and deep-nesting edge cases; fix stale comments
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: []
files_allowed: ["app/gemini.py", "tests/test_gemini.py"]
files_excluded: []
review: ["code", "security"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_gemini.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "CR-1: a non-str gemini_model (2 or [\"x\"]) is replaced by gemini.MODEL in the request URL for both check_key and translate_segments, with no TypeError; test_model_name_validated is parametrized with 2 (and [\"x\"]) in addition to the existing invalid, valid and None cases, which still pass"
  - "CR-3: HTTP 502 and 504 are retried exactly like 429/500/503 (retryDelay if present, else BACKOFF; at most MAX_TRIES = 3 requests); after the last try a GeminiError kind other with message \"Gemini request failed (HTTP 502)\" / \"(HTTP 504)\" and no key is raised; test_5xx_retried_then_ok is parametrized over 500, 502, 503 and 504 (sleeps == [5]), and a test shows three 504s give up after 3 requests with sleeps [5, 15]"
  - "SEC-5 (inner text): a 200 reply whose candidate text is a JSON array nested about 100000 levels deep (e.g. \"[\" * 100000 + \"]\" * 100000) is treated as a mismatch: the chunk is requested exactly twice, then fallback(chunk) is used and its text returned; no RecursionError escapes translate_segments; a test covers it"
  - "SEC-5 (outer body): a 200 reply whose raw HTTP body is nested about 100000 levels deep makes check_key raise GeminiError kind other (\"Gemini returned an unreadable response\") after exactly one request, without retry and without the key in the message; a test covers it (the net fixture can serve an object whose read() returns those bytes)"
  - "CR-2: the stale strings are updated: the BACKOFF comment (gemini.py:24) and the _post docstring (gemini.py:75) name the retried codes (429/500/502/503/504); the tests/test_gemini.py module docstring (line 1) and the net fixture docstring (line 43) say gemini._open is faked, not urlopen"
  - "existing tests in tests/test_gemini.py still pass unchanged in intent (key only in the x-goog-api-key header; 400/401/403 invalid_key; network errors; 429 gives rate_limited; 3xx refused with one request); no test touches the network"
  - "no new dependency; app/gemini.py stays UI-free; full suite passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

Close the TASK-011 review leftovers in the Gemini client so that a bad model name, a 502/504 or a deeply nested reply each either retries within bounds and then falls back, or fails with a readable, key-free `GeminiError`, and fix the stale comments.

## Context

- Findings: `reports/reviews/TASK-011-code.md` (CR-1 low, CR-2 low, CR-3 info) and `reports/reviews/TASK-011-security.md` (SEC-5 info). Source task and format reference: `tasks/TASK-011-harden-gemini-retries-fallback-redirects-and-mod.md`; handoff `reports/handoffs/TASK-011.md`.
- Testing rules: `project-context/project-profile.md` (Notes, Testing). Monkeypatching only; no network, no real ffmpeg, Whisper or NLLB. Use the existing fake `KEY`, the `net` fixture (patches `gemini._open` and `gemini.time.sleep`), and the `http_error`, `FakeResp`, `echo` and `segs` helpers in `tests/test_gemini.py`.
- **CR-1** (`app/gemini.py:76`, `_post`): `if not model or not _MODEL_RE.fullmatch(model)` raises `TypeError` for a truthy non-str. Decision: `if not isinstance(model, str) or not _MODEL_RE.fullmatch(model): model = MODEL`. Extend the `test_model_name_validated` parametrize list (`tests/test_gemini.py` around line 285) with `(2, gemini.MODEL)` and `(["x"], gemini.MODEL)`.
- **CR-3** (`app/gemini.py:89`): change `e.code in (429, 500, 503)` to include 502 and 504. Keep the last-try mapping: 429 raises `RATE_MSG` (kind `rate_limited`), every 5xx raises `Gemini request failed (HTTP <code>)` (kind `other`). Do not add a per-chunk NLLB fallback for 5xx; that remains out of scope as in TASK-011. Tests: parametrize `test_5xx_retried_then_ok` (around line 296) over `[500, 502, 503, 504]`; add a three-504s give-up test next to `test_three_500s_give_up`.
- **SEC-5**: Python's `json.loads` raises `RecursionError` (a `RuntimeError`, not a `ValueError`) on deeply nested input.
  - Outer body (`app/gemini.py:85` parse, `:103` `except ValueError`): catch `(ValueError, RecursionError)` there so it maps to the existing `GeminiError("other", "Gemini returned an unreadable response")`. No retry for this case (same as other unreadable bodies).
  - Inner text (`app/gemini.py:155` parse, `:164` except tuple): add `RecursionError` to the tuple so `_translate_chunk` returns `None` and the existing retry-once-then-fallback loop in `translate_segments` handles it.
  - `_retry_delay` already catches `Exception`; leave it.
  - Test data: build the nested string in the test (`"[" * 100000 + "]" * 100000`). For the outer-body test, the `net` queue item can be a small class whose `read()` returns those bytes and which supports the context manager protocol (like `FakeResp`, but with raw bytes). For the inner-text test, wrap the nested string as the candidate `text` (`FakeResp({"candidates": [{"content": {"parts": [{"text": nested}]}}]})`), queue it twice, and pass a `fallback`.
- **CR-2** (comments only): `app/gemini.py:24` (BACKOFF comment says "after HTTP 429"), `app/gemini.py:75` (`_post` docstring says "retries HTTP 429"), `tests/test_gemini.py:1` ("urlopen is faked") and `tests/test_gemini.py:43` ("served by urlopen"). Requests go through `gemini._open`.
- `CLAUDE.md:37` ("Tests mock `urlopen`") and the docs are out of scope here; TASK-015 updates them after this task.
- Rules (CLAUDE.md): no UI code in core modules; no new dependencies; the key appears only in the `x-goog-api-key` header, never in URLs, logs or error messages.

## Steps

1. Read `app/gemini.py`, `tests/test_gemini.py` (the `net` fixture and the TASK-011 hardening tests at the end of the file) and both TASK-011 reviews.
2. Add the failing tests: CR-1 parametrize cases, CR-3 parametrize and three-504s give-up, SEC-5 inner-text fallback and outer-body unreadable error.
3. Implement the `isinstance` check, the 502/504 retry codes, and `RecursionError` handling at both parse sites in `app/gemini.py`.
4. Fix the four stale comment/docstring strings (CR-2).
5. Run every validation command and record the exit codes and pass counts in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` if:
- the change needs files outside `files_allowed` (for example `app/translator.py`, `CLAUDE.md` or `docs/*`),
- an acceptance criterion is ambiguous,
- a dependency is missing, or
- a validation command cannot run in this environment.

Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-012.md` (see templates/handoff.md)

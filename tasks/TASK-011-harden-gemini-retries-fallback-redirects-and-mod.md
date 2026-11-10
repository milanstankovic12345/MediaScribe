---
id: TASK-011
title: Harden Gemini retries, fallback, redirects and model name; fix Settings and Transcribe Gemini UI
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-008"]
files_allowed: ["app/gemini.py", "tests/test_gemini.py", "app/screens/transcribe.py", "app/screens/settings_screen.py", "tests/test_transcribe_screen.py"]
files_excluded: []
review: ["code", "security"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_gemini.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "CR-1: a 200 reply with no text ({\"promptFeedback\":{\"blockReason\":\"SAFETY\"}} or {\"candidates\":[{\"finishReason\":\"RECITATION\"}]}) is treated as a mismatch: the chunk is requested exactly twice, then fallback(chunk) is called and a log line says local translation was used; without a fallback it raises GeminiError (kind other) instead of aborting on the first reply; tests cover both reply shapes"
  - "SEC-2: every Gemini request goes through an opener whose redirect handler refuses redirects (redirect_request returns None); a faked 301/302 reply yields exactly one request and GeminiError kind other whose message does not contain the key; tests cover the refusing handler and the 3xx mapping"
  - "SEC-3: a reply whose ids are Infinity, NaN or a non-integer type (e.g. [{\"i\": Infinity, \"t\": \"x\"}]) is treated as a mismatch (retry once, then fallback); no OverflowError escapes translate_segments; a test covers the Infinity case"
  - "SEC-4: a model name that does not fully match ^[A-Za-z0-9.\\-]+$ (e.g. \"../x?y\" or \"a/b\") is replaced by gemini.MODEL in the request URL for both check_key and translate_segments; a valid override (e.g. \"gemini-2.0-flash\") and None behave as before; tests cover invalid, valid and None"
  - "CR-2: HTTP 500 and 503 are retried with the same backoff as 429 (retryDelay if present, else BACKOFF) and at most MAX_TRIES (3) requests in total; after the last try a readable GeminiError kind other without the key is raised; tests cover 503-then-success and three 500s giving up (time.sleep monkeypatched)"
  - "existing 429, 400/401/403, network-error and request-shape tests still pass (the key is only in the x-goog-api-key header, never in the URL or any error message)"
  - "CR-3: the Transcribe 'Translate to' CTkOptionMenu (sub_target) has a command that calls self._update_guidance(), so changing the target shows or hides the Gemini guidance (code check; not visually verified unless a display is used)"
  - "CR-4: with GEMINI_API_KEY set, Settings 'Test connection' tests the environment key (not the entry or saved key) and the status text says the environment key is being tested; without the env var it behaves as before (entry key, else saved key); a Tk-free stub-self test with threading.Thread monkeypatched shows which key reaches the worker"
  - "CR-5: a stub-self test in tests/test_transcribe_screen.py runs TranscribeScreen._run with engine=translator.GEMINI_ENGINE, a non-Original target, a fake api_key and gemini_model, and asserts translator.translate receives that engine, key and model, translator.translate_segments is not called, and neither any _say message nor the returned Saved string contains the key"
  - "no new dependency; no test touches the network or runs real ffmpeg/Whisper/NLLB; full suite passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

Fix the TASK-008 review findings so that every Gemini failure mode (blocked reply, bad ids, 5xx, redirect, bad model name) either retries within bounds and then falls back per chunk, or fails with a readable, key-free error, and fix the three small Gemini UI and test gaps.

## Context

- Findings: `reports/reviews/TASK-008-code.md` (CR-1 medium; CR-2, CR-3, CR-4, CR-5 low) and `reports/reviews/TASK-008-security.md` (SEC-2 low; SEC-3, SEC-4 info). Source task: `tasks/TASK-008-add-optional-gemini-api-translation-with-setting.md`; handoff `reports/handoffs/TASK-008.md`. Precedent for this kind of follow-up: `tasks/TASK-010-fix-transcribe-embed-burn-validation-with-url-pl.md`.
- Testing rules: `project-context/project-profile.md` (Testing, Notes). Tests use monkeypatching only. No network, no real ffmpeg, Whisper or NLLB.
- **CR-1** (`app/gemini.py` `_text_of` / `_translate_chunk`): `_text_of` raises `GeminiError`, which the `except (ValueError, KeyError, TypeError)` in `_translate_chunk` does not catch. Decision: a `GeminiError` from `_text_of` (not from `_post`) makes `_translate_chunk` return `None`. The existing retry-then-fallback loop in `translate_segments` then handles it. Errors raised by `_post` (key, network, rate limit) must still propagate.
- **SEC-3** (same `try`): `int(x["i"])` on `Infinity` raises `OverflowError`. Decision: catch `ArithmeticError` as well, or require `type(x["i"]) is int`. Either way, Infinity, NaN and non-int ids count as a mismatch. Keep the current behaviour for the existing parametrized bad-id tests.
- **SEC-2** (`_post`): build a module-level opener once, using `urllib.request.build_opener(<HTTPRedirectHandler subclass whose redirect_request returns None>)`, and call its `open(req, timeout=TIMEOUT)` instead of `urllib.request.urlopen`. A refused 3xx then reaches `_post` as `HTTPError` with code 3xx. Map it to `GeminiError("other", "Gemini request failed (HTTP <code>)")` with no retry. TLS defaults stay unchanged. **The `net` fixture in `tests/test_gemini.py` currently patches `gemini.urllib.request.urlopen`.** Route requests through one patchable name, for example `gemini._open(req, timeout)` or the opener's `open`, and update the fixture to patch it. The fixture's queue and request recording stay as they are. To test the handler itself, call `redirect_request(...)` directly and check that the module opener includes it. Do not start a local HTTP server.
- **CR-2** (`_post`): treat 500 and 503 like 429 (same `BACKOFF` / `retryDelay`, same `MAX_TRIES` cap). On the last try, 500/503 raise the existing `Gemini request failed (HTTP <code>)` message (kind `other`), and 429 keeps `RATE_MSG`. Do not add a per-chunk NLLB fallback for 5xx. That would be a behaviour change beyond this task.
- **SEC-4** (`_post`): before formatting `ENDPOINT`, use `model` only if `re.fullmatch(r"[A-Za-z0-9.\-]+", model)`, otherwise `MODEL`. Do it in `_post`, so `check_key` and `translate_segments` are both covered. `app/gemini.py` stays UI-free and does not log here.
- **CR-3** (`app/screens/transcribe.py`, the `sub_target` `CTkOptionMenu` around line 61): add `command=lambda _v: self._update_guidance()`, the same as the existing `engine` menu.
- **CR-4** (`app/screens/settings_screen.py` `_test`): when `settings.get_gemini_key({})` is non-empty (the env var is set), test that key and set the status to something like "Testing GEMINI_API_KEY from environment...". Otherwise keep `entry or saved key`. Never show the key itself. Put the stub-self test in `tests/test_gemini.py`, which already imports `app.screens.settings_screen`. Call `SettingsScreen._test(stub)` unbound, with a `SimpleNamespace` stub (`key_entry.get`, `status.configure`, `test_btn.configure`, `cfg`). Monkeypatch `settings_screen.threading.Thread` to record `args`, and use `monkeypatch.setenv/delenv("GEMINI_API_KEY", ...)`.
- **CR-5** (`tests/test_transcribe_screen.py`): reuse the existing `env` fixture and `run` helper style. Call `TranscribeScreen._run(stub, ..., engine=translator.GEMINI_ENGINE, api_key=KEY, gemini_model="m")`, and monkeypatch `tmod.translator.translate` to record its positional args (signature `translate(segs, src_iso, target, engine, api_key, cb, log, model)`). The `_run` signature is in `app/screens/transcribe.py` around line 161.
- **Deferred (out of scope, record them in the handoff `next_steps` as still open):**
  - SEC-1 (key stored in plaintext in `%APPDATA%\yt-tool\config.json`; hardening via DPAPI `CryptProtectData` through `ctypes`) needs a separate task with a settings migration.
  - CR-6 (Gemini is called even when source equals target; the fallback raises for sources NLLB does not support, e.g. ja) touches `app/translator.py`, which is outside this scope.
- Docs: `docs/*` and `CLAUDE.md` are not in scope. If you think the redirect or 5xx behaviour needs a doc line, list it in the handoff `next_steps`.
- Rules (CLAUDE.md): no UI code in core modules; never touch widgets off the main thread; no new dependencies; never put a real key in tests (use the existing fake `KEY`).

## Steps

1. Read `app/gemini.py`, `tests/test_gemini.py` (the `net` fixture and the retry/fallback tests), and both TASK-008 reviews.
2. In `tests/test_gemini.py`, add failing tests for CR-1 (both blocked shapes), SEC-3 (Infinity id), SEC-4 (invalid, valid, None model), CR-2 (503 then OK; three 500s give up) and SEC-2 (refusing handler; 3xx maps to `other`, one request, keyless). Point the `net` fixture at the new request entry point.
3. Implement the `app/gemini.py` changes: the no-redirect opener, 5xx backoff, model-name check, and treating no-text and bad ids as a mismatch.
4. Add the CR-4 fix in `settings_screen.py` with its stub-self test in `tests/test_gemini.py`.
5. Add the CR-3 `command` in `transcribe.py`, and the CR-5 `_run` Gemini-branch test in `tests/test_transcribe_screen.py`.
6. Run every validation command and record the exit codes. Note that CR-3 was not visually verified unless you checked it on a display.

## Blockers

Stop and write a handoff with `status: blocked` if:
- the change needs files outside `files_allowed` (for example `app/translator.py` or `app/settings.py`),
- an acceptance criterion is ambiguous,
- a dependency is missing, or
- a validation command cannot run in this environment.

Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-011.md` (see templates/handoff.md)

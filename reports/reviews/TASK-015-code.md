---
task: TASK-015
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - CLAUDE.md
  - docs/blueprint.md
  - docs/techstack.md
  - app/gemini.py
  - app/translator.py
  - app/settings.py
  - app/secret_store.py
  - app/screens/transcribe.py
  - tests/test_gemini.py
  - tests/test_settings_secret.py
not_checked:
  - TASK-012..014 handoff texts (claims checked against code instead)
  - README.md, docs/prd.md, docs/tasks.md contents (mtimes only)
findings:
  - id: CR-1
    severity: medium
    title: techstack Gemini row omits retryDelay and the invalid/non-string gemini_model fallback listed in task acceptance 2
    location: docs/techstack.md:11
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: CLAUDE.md names translator.translate for every engine; the local path calls translate_segments directly
    location: CLAUDE.md:24
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: "at most 3 requests is per _post call; one chunk can make up to 6 requests before fallback"
    location: CLAUDE.md:37
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1: techstack Gemini row omits retryDelay and the gemini_model fallback (Medium, confidence 80)

- **Location:** `docs/techstack.md:11`
- **Impact:** Acceptance 2 names "the Gemini row of docs/techstack.md" among the files that state the behaviour as built, including "retryDelay if given" and the invalid/non-string `gemini_model` fallback to `gemini.MODEL`. The row covers retries and redirects only. CLAUDE.md:37 and blueprint.md:12 cover both. Step 4 of the task lists only "(retries, redirects)" for this row, so the task text is ambiguous. That is why this is medium and not a blocking high.
- **Reproduction:** `grep -n "retryDelay\|gemini_model" docs/techstack.md` finds no match.
- **Recommended fix:** Change the clause to "with backoff (server `retryDelay` if given, max 3 requests)". Add "an invalid or non-string `gemini_model` override falls back to the default model".

### CR-2: CLAUDE.md names translator.translate for every engine (Low, confidence 90)

- **Location:** `CLAUDE.md:24`
- **Impact:** The bullet reads "optional `translator.translate` (skipped for Original; ...)". `TranscribeScreen._run` (app/screens/transcribe.py:195-199) calls `translator.translate` only for the Gemini engine. The Local engine calls `translator.translate_segments` directly. Behaviour is the same, because `translate` sends non-Gemini runs to `translate_segments`. But a maintainer who edits `translate` to change Local behaviour would see no effect. blueprint.md:26 has the right order.
- **Reproduction:** transcribe.py:199. The `else` branch calls `translator.translate_segments(...)`.
- **Recommended fix:** Change it to "`translator.translate_segments` (Local) or `translator.translate` (Gemini; ...)".

### CR-3: "at most 3 requests" is per _post call (Info, confidence 90)

- **Location:** CLAUDE.md:37, blueprint.md:12, techstack.md:11
- **Impact:** `_post` caps one call at `MAX_TRIES = 3`. But `_translate_chunk` catches `GeminiError` and returns None, and `translate_segments` retries the chunk once. So under sustained 429/5xx errors one chunk sends up to 6 requests before the NLLB fallback. The docs match the acceptance wording, but a reader may assume the cap is per chunk. The older blueprint wording "a chunk with wrong ids is retried once" also understates the behaviour: any GeminiError (key, network, rate limit) is retried once and then translated locally.
- **Reproduction:** Fake `gemini._open` so it always raises HTTP 429. One chunk makes 6 requests, then `fallback` runs.
- **Recommended fix:** Optional. Write "max 3 requests per call; a failed chunk is retried once, then translated locally".

## Verified claims (no finding)

- CLAUDE.md has no `urlopen`. It names `gemini._open`, and tests/test_gemini.py:55 monkeypatches `gemini._open`. The doc part of TASK-011 CR-2 is resolved.
- gemini.py:24-25 and 63-99: retries 429/500/502/503/504, uses `retryDelay` (capped at 120 s), `MAX_TRIES = 3`. `_NoRedirect` returns None, so a 3xx becomes HTTPError, mapped to kind other. `_post` 76-77: a non-string or regex-invalid model falls back to MODEL.
- translator.py:172 sends same-language runs to `translate_segments`, which transliterates only for Serbian (Latin) (135-138). Lines 176-181: with an unsupported source, the chunk keeps its text and a line is logged.
- settings.save writes only `gemini_api_key_enc`. settings.load decrypts it, treats SecretStoreError as an empty key, and keeps a legacy plaintext key until the next save encrypts it. The env var wins in `get_gemini_key`. secret_store calls CryptProtectData through ctypes (no machine flag, so the key is per user) and raises on non-Windows.
- The test list includes test_gemini.py and test_settings_secret.py. The real-DPAPI tests are skipif non-win32 (lines 48, 122).
- README.md (2026-10-29), docs/prd.md (11-09) and docs/tasks.md (11-10 14:20) have mtimes before the edits (18:18), so they were not changed.

## Validation re-run (this session)

- task python -c check: exit 0.
- `.venv/Scripts/python -m pytest -q`: exit 0, 170 passed, 2 skipped. This matches the handoff. Checked with `-rs`: the 2 skips are the opt-in e2e tests. The DPAPI tests ran (13 passed in test_settings_secret.py).

## Coverage statement

Inspected: the full on-disk text of CLAUDE.md, docs/blueprint.md and docs/techstack.md (gitignored, so git diff is empty), checked against app/gemini.py, translator.py, settings.py, secret_store.py, the translate branch of screens/transcribe.py, and the test fakes and skip markers. Ran both validation commands. Not checked: the TASK-012..014 handoff texts, the contents of the out-of-scope docs (mtimes only), real Gemini network calls, and DPAPI under another user. reports/handoffs/TASK-015.md.rejected is left over for the orchestrator to remove. No findings is not proof that the docs are complete.

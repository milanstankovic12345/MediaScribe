---
task: TASK-008
kind: security
reviewer: security-reviewer
model: claude-opus-5-5
round: 1
verdict: approve
scope_checked:
  - app/gemini.py
  - app/screens/settings_screen.py
  - app/settings.py
  - app/translator.py
  - app/screens/transcribe.py
  - app/screens/base.py
  - app/ui.py
  - app/subtitles.py
  - tests/test_gemini.py
not_checked:
  - Live Gemini API calls (no key; external system)
  - docs and CLAUDE.md prose
  - UI rendering
  - Dependency audit (no new dependency)
findings:
  - id: SEC-1
    severity: low
    title: Gemini API key stored in plaintext in roaming APPDATA config.json
    location: app/settings.py:50-54
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-2
    severity: low
    title: urllib follows redirects and forwards x-goog-api-key to the redirect target
    location: app/gemini.py:64-67
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-3
    severity: info
    title: OverflowError on an Infinity id escapes parsing and skips retry and fallback
    location: app/gemini.py:137
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-4
    severity: info
    title: gemini_model config value interpolated into URL path unvalidated
    location: app/gemini.py:61
    confidence: 70
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### SEC-1 — Plaintext key in roaming APPDATA (Low, confidence 95)

- **Category:** CWE-312; OWASP A02.
- **Location:** `app/settings.py:50-54`, `app/screens/settings_screen.py:82-85`.
- **Exploit scenario:** a process running as the same user, a backup or sync tool, or a roaming-profile server copy of `config.json` exposes the key. Impact: quota abuse of a revocable free-tier key. The task chose this storage on purpose (no keyring dependency).
- **Fix (hardening):** DPAPI `CryptProtectData` through `ctypes` (stdlib), or document the `GEMINI_API_KEY` env var as the no-disk option.
- **Test:** after Save, the file must not contain the key, and `get_gemini_key(load())` must still return it.

### SEC-2 — Redirects forward the API key header (Low, confidence 80)

- **Category:** CWE-200; OWASP A05.
- **Location:** `app/gemini.py:64-67`.
- **Evidence:** in Python 3.11.15, `HTTPRedirectHandler.redirect_request` keeps every header except content-length and content-type (checked in the source). A 301/302/303 to the POST is followed as a GET to any host or to `http://`, and the key goes with it.
- **Exploit scenario:** needs the Google endpoint itself to send a redirect. TLS verification is on (CERT_REQUIRED, check_hostname), so a network attacker cannot inject one. This is a defence-in-depth gap.
- **Fix:** an opener with a redirect handler whose `redirect_request` returns `None`, so a 3xx becomes `HTTPError` and then `GeminiError("other")`.
- **Test:** fake a 302 and assert there is no second request and no key in the error.

### SEC-3 — OverflowError escapes response parsing (Info, confidence 95)

- **Category:** CWE-20.
- **Location:** `app/gemini.py:137` (`int(x["i"])`). The except on line 143 does not catch OverflowError.
- **Evidence:** reproduced with a faked urlopen returning `[{"i": Infinity, "t": "x"}]`. It raised OverflowError, skipped the retry and the NLLB fallback, and the job failed. No key in the message. Object, string, `[1,2]`, `t: null` and `null` all fell back correctly.
- **Fix:** catch `ArithmeticError` too, or require `isinstance(x["i"], int)`.

### SEC-4 — Unvalidated model name in URL path (Info, confidence 70)

- **Category:** CWE-20.
- **Location:** `app/gemini.py:61`, from `cfg["gemini_model"]`.
- **Assessment:** the host is fixed, so only the path or query on googleapis.com can change. The source is local config. InvalidURL messages show the URL, not the key.
- **Fix:** `re.fullmatch(r"[A-Za-z0-9.\-]+", model)`, otherwise use MODEL.

## Verified claims

- The key goes only in the `x-goog-api-key` header, not in the URL or body. Covered by a test and by reading `_post`.
- Errors are fixed strings raised `from None`, and the HTTP body is never included. A key containing CRLF made http.client raise a ValueError whose text includes the key; `_post` caught it and raised the keyless "unreadable response". No leak and no header injection.
- The key is not logged. `api_key` only reaches `translator.translate`. The log, the error popup and the Done popup get `str(e)` or the file list.
- TLS verification is on by default (OpenSSL 3.5.7). Timeout is 60 s. 429 handling is capped at 3 tries, with retryDelay capped at 120 s.
- The env key is never persisted: `collect_cfg` returns `{}`.
- Text goes to Google only when Gemini is selected and the target is not Original. Test connection sends a fixed prompt.
- At the SRT sink, `to_cues` collapses whitespace, so model output, even prompt-injected via a hostile video, cannot add cue blocks.
- No committed key: a grep for the AIza prefix found nothing, and the tests use a fake key. tests/test_gemini.py was re-run here: 24 passed.

## Coverage statement

Reviewed: Settings screen actions and test worker, Transcribe Translator branch (`_validate`, `_args`, `_run`), settings load/save/get_gemini_key, all of gemini.py, the base worker error and Done paths, and SRT writing. Applied: OWASP baseline, secrets, input validation. Tools: in-memory probes (faked urlopen, unreachable localhost), urllib source inspection, pytest. Not reviewed: live API, UI rendering, docs, deps. This review does not show the feature is secure. It records only what was checked.

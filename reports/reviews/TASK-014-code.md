---
task: TASK-014
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/secret_store.py
  - app/settings.py
  - tests/test_settings_secret.py
  - app/screens/settings_screen.py (callers, read only)
  - app/ui.py (load and _close, read only)
not_checked:
  - Roaming/domain DPAPI master-key failures
  - Non-Windows execution
  - UI not visually verified
findings:
  - id: CR-1
    severity: low
    title: Failed save status is overwritten by Connected (key saved)
    location: app/screens/settings_screen.py:81-84
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: The no-leak assertion in the decrypt-failure test is vacuous
    location: tests/test_settings_secret.py:68-80
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: Identical if/else branches in secret_store._run
    location: app/secret_store.py:43-47
    confidence: 100
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: Undecryptable blob is dropped at the next save (App._close always saves)
    location: app/settings.py:41-46
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-5
    severity: info
    title: Process-global argtypes on windll.crypt32
    location: app/secret_store.py:14-32
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 Failed save status is overwritten (Low, 95)
- Location: `app/screens/settings_screen.py:81-84` (`_save`), and the same at 86-90 (`_disconnect`).
- Impact: when `settings.save` raises (now also when `protect` fails), `_persist` shows "Could not write the settings file." and `_refresh_status` immediately replaces it with "Connected (key saved)". The key is not persisted and the user is not told. This existed before; the change adds a new way for the save to fail (relates to the encryption-failure criterion).
- Reproduction: patch `secret_store.protect` to raise `SecretStoreError`, enter a key, click Save.
- Fix: `_persist` returns a bool; call `_refresh_status()` only on success.

### CR-2 The no-leak assertion in the decrypt-failure test is vacuous (Low, 90)
- Location: `tests/test_settings_secret.py:68-80` (decryption-failure criterion)
- Impact: KEY is never in the payload, so `assert KEY not in out` passes even if `load` printed the token. The production code is clean (no print or log); this is a test gap only.
- Reproduction: add `print(enc)` in the `except` branch of `load`. The test still passes.
- Fix: put KEY in the payload, e.g. `KEY + "!!"` for bad base64, and `base64(KEY)` for the raising case.

### CR-3 Identical if/else branches in `_run` (Low, 100)
- Location: `app/secret_store.py:43-47`. Both branches make the same call. A future edit to one branch only (entropy, description) would break round-trips.
- Fix: collapse into a single call.

### CR-4 Undecryptable blob is dropped at the next save (Info, 95)
- `load` maps a decrypt failure to an empty key and drops the token. `App._close` always saves, so a transient DPAPI failure (e.g. a roaming profile) permanently loses the stored key. This matches the task design; it could be noted in the TASK-015 docs.

### CR-5 Process-global argtypes (Info, 80)
- `_api()` sets argtypes on the shared `ctypes.windll.crypt32` function objects on every call, and the plaintext buffer is not zeroed. Optional: use a private `ctypes.WinDLL("crypt32")` created once.

## Acceptance check
All acceptance criteria are met; CR-1 and CR-2 are the caveats. Probes I ran (`python -c`, temp directory): non-str input, invalid base64, a non-ASCII token, a token with a leading space or trailing newline, an empty token, and a non-DPAPI blob each raise `SecretStoreError`, with messages that contain no plaintext (`from None`). For `load`, enc values of null, a list or an empty string each give an empty key without raising; enc takes precedence over a legacy plaintext key. `save` stores only `gemini_api_key_enc`, strips the key, calls `protect` before writing and does not mutate its input.

## Validation (re-run by reviewer)
- `.venv/Scripts/python -m pytest tests/test_settings_secret.py -q`: exit 0, 13 passed (real DPAPI tests ran on win32).
- `.venv/Scripts/python -m pytest -q`: exit 0, 170 passed, 2 skipped (opt-in e2e). Matches the handoff.

## Coverage statement
Read in full: secret_store.py, settings.py (diff vs cf0c2c1) and test_settings_secret.py. Read callers: settings_screen.py `_persist/_save/_disconnect/_refresh_status`, ui.py `load/_close`, transcribe.py `get_gemini_key`. Not checked: non-Windows runtime, roaming/domain DPAPI behaviour, the UI (not visually verified). No blocking findings, but that does not prove the code is correct.

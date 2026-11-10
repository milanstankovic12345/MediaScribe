---
task: TASK-016
kind: security
reviewer: security-reviewer
model: claude-opus-5-5
round: 1
verdict: approve
scope_checked:
  - app/secret_store.py
  - app/screens/settings_screen.py
  - app/settings.py (save/load/get_gemini_key, data path into secret_store)
  - tests/test_settings_secret.py
  - git diff 34d954d -- app/secret_store.py app/screens/settings_screen.py
not_checked:
  - Import of app.secret_store on a real non-Windows interpreter (module now imports ctypes.wintypes at top level; no non-Windows Python available here)
  - Live UI behaviour of the Settings screen (not visually verified)
  - yt-dlp real cookie-decryption path end to end (emulated with a yt-dlp-style raw CryptUnprotectData call instead)
findings:
  - id: SEC-1
    severity: info
    title: SEC-2 regression test misses a regression that mutates windll with a stable module-level DATA_BLOB when it runs after other real-DPAPI tests
    location: tests/test_settings_secret.py:159
    confidence: 70
    status: open
    verified: true
    acceptance_ref: null
  - id: SEC-2
    severity: info
    title: Failed Disconnect clears the key in memory but leaves the encrypted key on disk (pre-existing; now correctly reported to the user)
    location: app/screens/settings_screen.py:89-93
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
---

> Saved by the orchestrator on the user's instruction. The security-reviewer's own save was refused by the read-only guard. The text is the reviewer's report. The only change: SEC-1 `acceptance_ref` is now null, because the schema accepts only RA-NNN ids and the finding is open, not accepted.

## Summary

The three TASK-016 fixes are present, and the reviewer checked each one directly instead of relying on the implementer's claims:

- **SEC-1 (encode errors).** `protect("a\ud800b")` raises `SecretStoreError('text is not encodable')` with `__cause__ is None`, `__context__ is None` and `__suppress_context__ True`. The message contains no plaintext. The encode check runs before `_run`, so it works on every platform. `settings.save` calls `protect` before `mkdir`/`write_text`, so the file is left alone (`test_save_lone_surrogate_keeps_file` passes).
- **SEC-2 (shared ctypes prototypes).** In a fresh process, after `protect`/`unprotect`, `ctypes.windll.crypt32.CryptUnprotectData.argtypes` is still `None`, `CryptProtectData.restype` is still the default `c_long`, and `kernel32.LocalFree.argtypes` is still `None`. The private `WinDLL` handles are separate from the `windll` ones. A yt-dlp-style call through `windll.crypt32.CryptUnprotectData` with the caller's own `DATA_BLOB` still works after `secret_store` has been used. `DATA_BLOB` is defined once at module level. The lazy init assigns `_dlls` only after the prototypes are set, so the worst a race can do is build a second, identical private handle pair.
- **CR-1 (status on save failure).** `_persist` returns a bool, and `_save`/`_disconnect` call `_refresh_status` only when it returns True. If a Disconnect write fails, the user now sees "Could not write the settings file." instead of a misleading "Not connected".

No Critical, High, Medium or Low issues were found. There are two info notes.

## Findings

| id | severity | category | location | confidence | status |
|---|---|---|---|---|---|
| SEC-1 | info | Test coverage gap (OWASP A04, regression guard) | tests/test_settings_secret.py:159 | 70 | open |
| SEC-2 | info | CWE-459 Incomplete Cleanup (pre-existing) | app/screens/settings_screen.py:89-93 | 80 | open |

### SEC-1: The SEC-2 regression test misses one kind of regression (Info, confidence 70)

- **Verified:** the test catches the original TASK-014 defect even when it runs after `test_roundtrip_real`/`test_real_dpapi`, because the 34d954d code builds a new `DATA_BLOB` class, and so a new `POINTER(DATA_BLOB)`, on every call. A probe confirmed the snapshot changes. This narrows TASK-016-code.md CR-1.
- **Gap:** a future change that goes back to `ctypes.windll.crypt32` but keeps the module-level `DATA_BLOB` would pass in a full-file run. The earlier real-DPAPI tests would already have set the shared prototypes to identical values. The test fails only when run on its own.
- **Impact:** a regression that brings back the yt-dlp `ctypes.ArgumentError` breakage could get through CI. This affects availability, not confidentiality.
- **Fix:** add a check that does not depend on test order, e.g. assert `secret_store._api()[0] is not ctypes.windll.crypt32` and `secret_store._api()[0].CryptUnprotectData is not ctypes.windll.crypt32.CryptUnprotectData`, or run the round-trip in a fresh `subprocess`.
- **How to test the fix:** temporarily point `_api()` at `ctypes.windll.*` and run the whole file. The test must fail.

### SEC-2: A failed Disconnect leaves the encrypted key on disk (Info, pre-existing, confidence 80)

- **Scenario:** the user clicks Disconnect and `settings.save` raises `OSError`. `cfg["gemini_api_key"]` is already `""`, but `gemini_api_key_enc` is still in the file, so the key comes back on the next start. The user now sees "Could not write the settings file."
- **Impact:** low. The key stays DPAPI-protected for the same Windows user. This is out of scope for TASK-016 and belongs in the backlog.
- **Fix (later task):** on a failed save, put the previous key back in `cfg` or reload it from disk. The status line could also say the saved key was not removed.
- **How to test:** stub `settings.save` to raise `OSError`, call `_disconnect`, and assert that `cfg` and the status match what is on disk.

## Not findings (checked and dismissed)

- **Plaintext in the exception chain:** none. `raise ... from None` sits outside the `except` block, and both `__context__` and `__cause__` are `None`.
- **A `str` subclass with a hostile `.encode`:** cannot be reached. The only caller passes `key.strip()`, which always returns a plain `str`.
- **DLL planting through `ctypes.WinDLL("crypt32")`/`("kernel32")`:** both are KnownDLLs loaded from System32. The risk is the same as with `windll`.
- **`LocalFree`** still runs in `finally`, `CRYPTPROTECT_UI_FORBIDDEN` is still passed, and every failure in `_run` still becomes `SecretStoreError` with no chained context.

## Coverage statement

**Inspected:** the full diff 34d954d..HEAD for `app/secret_store.py` and `app/screens/settings_screen.py`, the current versions of both files, the data path from the Settings `key_entry` through `_save`, `settings.save`, `secret_store.protect` and `_run` to DPAPI and `config.json`, the load path through `settings.load` and `unprotect`, and `tests/test_settings_secret.py`.

**Commands run (Windows, Python 3.11.15):** `.venv/Scripts/python -m pytest tests/test_settings_secret.py -q` (exit 0, 19 passed); `.venv/Scripts/python -m pytest -q` (exit 0, 176 passed, 2 skipped); the SEC-2 test on its own (1 passed); a fresh-process probe fed through stdin (no files written).

**Not reviewed:** a real non-Windows import (the app targets Windows only), live UI rendering, and the rest of the app outside TASK-016.

This review does not establish that the application is secure. It covers only the items listed above.

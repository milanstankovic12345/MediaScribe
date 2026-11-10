---
task: TASK-016
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/secret_store.py
  - app/screens/settings_screen.py
  - app/settings.py
  - tests/test_settings_secret.py
not_checked:
  - Real non-Windows import of app.secret_store (simulated via sys.platform patch only)
  - Live UI (not visually verified)
findings:
  - id: CR-1
    severity: medium
    title: SEC-2 regression test passes vacuously when run after the other real-DPAPI tests
    location: tests/test_settings_secret.py:159
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: Module-level ctypes imports placed mid-module after constants
    location: app/secret_store.py:14
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: Pre-existing raise inside except with from None keeps __context__ in unprotect and _run
    location: app/secret_store.py:88
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - SEC-2 regression test passes vacuously in file order (Medium, confidence 95)

- **Location:** `tests/test_settings_secret.py:159-169`
- **Impact:** The before-snapshot is taken after test_roundtrip_real and test_real_dpapi already ran DPAPI. If secret_store regressed to writing the shared windll prototypes, those writes would already be present, so before == after and the test passes.
- **Reproduction:** reviewer patched `secret_store._api` in memory with the pre-TASK-016 shared-windll version. Whole file: 19 passed (not detected). The test alone: 1 failed at line 169.
- **Recommended fix:** at test start, `monkeypatch.setattr(secret_store, "_dlls", None)` and set the six shared attributes to sentinels via monkeypatch before snapshotting. Literal acceptance wording is met, so not blocking.

### CR-2 - ctypes imports mid-module (Low, confidence 90)

- **Location:** `app/secret_store.py:14-15`
- **Impact:** No functional effect; imports sit after constants (E402 pattern), which hides the dependency.
- **Reproduction:** read lines 1-19.
- **Recommended fix:** move both imports to the top import block.

### CR-3 - Pre-existing __context__ retention (Info, confidence 90)

- **Location:** `app/secret_store.py:62-63` and `app/secret_store.py:87-88` (unchanged lines)
- **Impact:** raise ... from None inside an except still sets __context__. In unprotect, that keeps the UnicodeDecodeError, whose .object holds the decrypted bytes. Out of scope; not worsened. Forward to security / orchestrator.
- **Reproduction:** Python semantics; the implementer avoided this in protect for the same reason.
- **Recommended fix (follow-up):** flag, then raise outside the except, as protect does.

## Verification of handoff claims

- SEC-1 confirmed: protect of a lone surrogate gives SecretStoreError("text is not encodable"), __cause__ None, __context__ None, no plaintext. With sys.platform patched to linux, the encode check still fires first. settings.save leaves the file byte-identical.
- SEC-2 confirmed: private WinDLL handles cached in _dlls; DATA_BLOB defined once at module level. After protect/unprotect, shared windll argtypes stay None, and a yt-dlp-style shared windll CryptUnprotectData call with its own DATA_BLOB class succeeds.
- CR-1 (TASK-014) confirmed: _persist returns bool; _save/_disconnect refresh only on success. The three stub tests match the acceptance wording.
- Scope: only the 3 allowed files changed; no new dependency.

## Validation (re-run by reviewer)

- `.venv/Scripts/python -m pytest tests/test_settings_secret.py -q`: exit 0, 19 passed
- `.venv/Scripts/python -m pytest -q`: exit 0, 176 passed, 2 skipped (opt-in e2e)

## Coverage statement

Inspected: the full diff vs 34d954d, the full test file (gitignored, read directly), and the secret_store callers in app/settings.py. Ran both validation commands plus in-memory mutation, interop and SEC-1 checks. Not checked: a real non-Windows import, live UI, real yt-dlp cookie extraction. No findings beyond these does not prove the code is correct.

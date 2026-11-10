---
task: TASK-014
kind: security
reviewer: security-reviewer
model: claude-opus-5-5
round: 1
verdict: approve
scope_checked:
  - app/secret_store.py
  - app/settings.py
  - tests/test_settings_secret.py
  - app/screens/settings_screen.py
  - app/ui.py
  - .venv/Lib/site-packages/yt_dlp/cookies.py
not_checked:
  - real APPDATA yt-tool config.json (deliberately not read)
  - whether a CTkEntry can yield a lone surrogate (SEC-1 reachability)
  - supply chain (no new dependency)
findings:
  - id: SEC-1
    severity: low
    title: protect raises UnicodeEncodeError instead of SecretStoreError for text with lone surrogates
    location: app/secret_store.py:63
    confidence: 70
    status: open
    verified: true
    acceptance_ref: null
  - id: SEC-2
    severity: info
    title: _api overwrites argtypes on shared ctypes.windll.crypt32 prototypes with a per-call DATA_BLOB class
    location: app/secret_store.py:14-32
    confidence: 90
    status: open
    verified: true
    acceptance_ref: null
  - id: SEC-3
    severity: info
    title: A decryption failure followed by any save permanently deletes the stored encrypted key
    location: app/settings.py:41-46
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-4
    severity: info
    title: Residual risk of DPAPI CurrentUser without entropy and legacy plaintext remnants
    location: app/secret_store.py:45
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

| id | severity | category | location | confidence | status |
|---|---|---|---|---|---|
| SEC-1 | low | CWE-755 Improper Handling of Exceptional Conditions | app/secret_store.py:63 | 70 | open |
| SEC-2 | info | CWE-710 global ctypes prototype mutation | app/secret_store.py:14-32 | 90 | open |
| SEC-3 | info | OWASP A04 design consequence (availability) | app/settings.py:41-46, app/ui.py:52-58 | 90 | open |
| SEC-4 | info | CWE-312 residual, OWASP A02 | app/secret_store.py:45, app/settings.py:57-67 | 80 | open |

### SEC-1 - protect leaks UnicodeEncodeError instead of SecretStoreError (Low, confidence 70)

- **Location:** app/secret_store.py:63. text.encode("utf-8") runs outside the try block in _run, so its exception is not wrapped.
- **Verified:** protect("abc\ud800def") raises UnicodeEncodeError, which is not an OSError. Its message names only the bad character and its position. unprotect is fine: a non-ASCII token raises SecretStoreError.
- **Scenario:** a key containing a lone surrogate is entered and saved. SettingsScreen._persist catches only OSError, so a traceback goes to stderr and no status is shown. In App._close the exception skips self.destroy(), so the window will not close. The plaintext is never written, so the save fails closed. This breaks task acceptance 1 (every failure raises SecretStoreError) and acceptance 7.
- **Fix:** in protect, catch UnicodeError around the encode and raise SecretStoreError("text is not encodable") from None.
- **Test:** pytest.raises(SecretStoreError) for protect("a\ud800b"). Also check that settings.save with that key raises OSError and leaves the file unchanged.

### SEC-2 - Shared crypt32 prototypes are overwritten on every call (Info, confidence 90)

- **Location:** app/secret_store.py:14-32. Each call redefines DATA_BLOB and sets argtypes on the process-global ctypes.windll.crypt32 and kernel32 function objects.
- **Verified:** after one protect/unprotect round-trip, yt_dlp.cookies._decrypt_windows_dpapi raises ctypes.ArgumentError (expected LP_DATA_BLOB instance instead of pointer to DATA_BLOB). Two threads calling _run at once can fail the same way. Both cases fail closed.
- **Impact today:** none reachable. The app does not use cookiesfrombrowser, and settings load/save run on the main thread.
- **Fix:** define DATA_BLOB once at module level and set argtypes once on private ctypes.WinDLL("crypt32") and ctypes.WinDLL("kernel32") instances, loaded lazily and only on win32.
- **Test:** after protect("x"), ctypes.windll.crypt32.CryptUnprotectData.argtypes is None.

### SEC-3 - An undecryptable key is silently erased on the next save (Info, confidence 90)

- **Location:** settings.load sets gemini_api_key to "" on failure, settings.save then writes no gemini_api_key_enc, and App._close (app/ui.py:52-58) saves on every exit.
- **Scenario:** the DPAPI master key becomes unavailable, for example after an admin password reset, a profile migration, a copy to another machine or a transient failure. The next app close deletes the ciphertext for good, and the Settings screen just shows Not connected.
- **Assessment:** this follows the final user decision in task acceptance 4 (undecryptable means unset) and fails safe. It is reported so the user knows about the data loss. Optional fix: keep the undecryptable token under a private field and write it back while the in-memory key stays empty.

### SEC-4 - Residual risk (Info, confidence 80)

- CurrentUser DPAPI without entropy (handoff decision): any process running as the same Windows user can decrypt the token. That is inherent to DPAPI, and a constant entropy would not change it materially. The change protects against the file being copied, synced or backed up to another account or machine. It does not protect against same-user malware.
- A legacy plaintext key stays in config.json until the next save. The file is rewritten in place, not atomically, so earlier plaintext versions can survive in File History, OneDrive or roaming copies, backups or freed disk clusters. The key is not zeroed in process memory.
- **Recommendation (user decision):** if the key was ever stored in plaintext in a backed-up or synced profile, rotate it.

## Verified implementer claims

- pytest tests/test_settings_secret.py -q gives 13 passed, 0 skipped. The real DPAPI tests ran on win32.
- pytest -q gives 170 passed, 2 skipped, matching the handoff.
- The ctypes signatures match the documented 7-argument CryptProtectData and CryptUnprotectData. CRYPTPROTECT_UI_FORBIDDEN is passed. The output pbData is freed with LocalFree in a finally block, and nothing is freed when a call fails.
- All SecretStoreError messages are fixed strings, and none carries the plaintext.
- save calls protect before creating the directory or writing the file. It does not mutate its input and writes only gemini_api_key_enc for a non-empty key.
- load pops gemini_api_key_enc and maps every SecretStoreError to an empty key, including non-str, null and bad base64 values. No print or logging was added.
- The GEMINI_API_KEY env override is unchanged. SettingsScreen.collect_cfg returns an empty dict. No new dependency was added.

## Coverage statement

Inspected: app/secret_store.py in full, the diff and full text of app/settings.py, tests/test_settings_secret.py, all callers of settings.load and settings.save (app/ui.py, app/screens/settings_screen.py), a grep of app for other config writers or key logging, and the in-process crypt32 user in yt-dlp. I ran both validation commands and local offline probes of protect/unprotect edge cases plus the yt-dlp interference check. References: owasp-top10 (A02, A04) and secrets handling. Not reviewed: the real config file of the user, the unchanged Gemini network code, and supply chain. No SAST was run. This review does not show that the key storage is secure. It covers only the items listed.

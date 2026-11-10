---
id: TASK-016
title: Fix secret_store encode errors, private ctypes prototypes and save-failure status
status: review
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-014"]
files_allowed: ["app/secret_store.py", "app/screens/settings_screen.py", "tests/test_settings_secret.py"]
files_excluded: []
review: ["code", "security"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_settings_secret.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "SEC-1: secret_store.protect(\"a\\ud800b\") raises secret_store.SecretStoreError (not UnicodeEncodeError), raised with `from None` (no __context__ / __cause__ chain), and its str() does not contain \"a\\ud800b\"; this holds on every platform because the encode check runs before any DPAPI call"
  - "SEC-1: settings.save(cfg, path) with cfg[\"gemini_api_key\"] = \"a\\ud800b\" raises OSError and the file at path keeps its previous content byte for byte (test pre-writes a file under tmp_path, then compares)"
  - "SEC-2: secret_store no longer reads or modifies ctypes.windll.crypt32 / ctypes.windll.kernel32; it uses private ctypes.WinDLL(\"crypt32\") and ctypes.WinDLL(\"kernel32\") instances whose argtypes/restype are set once (lazily or at import, only on win32), and DATA_BLOB is a single module-level class (not redefined per call); importing app.secret_store on non-Windows still works"
  - "SEC-2 test (skipif sys.platform != \"win32\"): snapshot argtypes and restype of ctypes.windll.crypt32.CryptProtectData, ctypes.windll.crypt32.CryptUnprotectData and ctypes.windll.kernel32.LocalFree, run unprotect(protect(\"FAKE-KEY-123\")) twice, and assert the round-trip returns the key and all six snapshot values are unchanged"
  - "CR-1: SettingsScreen._persist returns True when settings.save succeeds and False when it raises OSError; _save and _disconnect call _refresh_status only when _persist returned True, so after a failed save the status label's last text is \"Could not write the settings file.\""
  - "CR-1 tests on a stub self (types.SimpleNamespace, no window, settings.save monkeypatched, GEMINI_API_KEY unset): _save with a failing save ends with status \"Could not write the settings file.\"; _save with a succeeding save ends with \"Connected (key saved)\"; _disconnect with a failing save ends with \"Could not write the settings file.\""
  - "existing tests in tests/test_settings_secret.py, tests/test_gemini.py and tests/test_core.py pass unchanged; the full suite passes; no new dependency; no test touches the network or writes outside tmp_path"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

Close TASK-014 review findings SEC-1, SEC-2 and CR-1: `protect` wraps encode failures in `SecretStoreError`, `secret_store` stops mutating process-wide ctypes prototypes, and the Settings screen keeps its error status when saving fails.

## Context

- Findings (read these sections only):
  - `reports/reviews/TASK-014-security.md` SEC-1 (`app/secret_store.py:63`: `text.encode("utf-8")` runs outside the error wrapping in `_run`) and SEC-2 (`app/secret_store.py:14-32`: `_api()` redefines `DATA_BLOB` and sets `argtypes` on the shared `ctypes.windll.crypt32` / `kernel32` function objects on every call, which breaks yt-dlp's `_decrypt_windows_dpapi` with `ctypes.ArgumentError`).
  - `reports/reviews/TASK-014-code.md` CR-1 (`app/screens/settings_screen.py:76-91`: `_persist` shows the error, then `_save` / `_disconnect` call `_refresh_status`, which overwrites it).
- **Out of scope:** the other TASK-014 findings (CR-2 vacuous no-leak assertion, CR-3 identical if/else branches in `_run`, CR-4 / SEC-3 undecryptable key dropped on save, SEC-4 residual risk, CR-5 plaintext buffer zeroing). Do not fix them here. If you rewrite `_run` for SEC-2 and the identical branches go away as a side effect, that is fine, but do not change behaviour beyond these three findings.
- Design:
  - SEC-1: in `protect`, wrap `text.encode("utf-8")` in `try/except UnicodeError` and `raise SecretStoreError("text is not encodable") from None`. Use a fixed message with no plaintext.
  - SEC-2: define `DATA_BLOB` once at module level (it needs only `ctypes` / `ctypes.wintypes`, which import fine on any OS). Build the private `ctypes.WinDLL("crypt32")` / `ctypes.WinDLL("kernel32")` handles and their prototypes once (cache them in a module global, or set them up at import inside `if sys.platform == "win32"`). Setting identical prototypes twice from a racing lazy init is harmless. Keep the existing `CRYPTPROTECT_UI_FORBIDDEN`, `LocalFree` in `finally`, and the "every failure raises SecretStoreError" behaviour. The non-win32 path still raises `SecretStoreError`.
  - CR-1: `_persist` returns `bool`. `_save` / `_disconnect` do `if self._persist(): self._refresh_status()`. No other UI change.
- Stub-self test pattern: `tests/test_gemini.py:344-365` (`_settings_stub`, which calls `SettingsScreen._test(st)` on a `SimpleNamespace`). For `_save` / `_disconnect`, the stub must provide `cfg`, `key_entry` (`get`, `delete`), `status.configure` that records `text`, and `_persist` / `_refresh_status` bound to the real methods, e.g. `st._persist = lambda: ss.SettingsScreen._persist(st)`. Monkeypatch `ss.settings.save` (or `settings.save`) to raise `OSError` or to succeed. `monkeypatch.delenv("GEMINI_API_KEY", raising=False)`.
- Put all new tests in `tests/test_settings_secret.py` (the only test file in scope).
- Testing rules: `project-context/project-profile.md` (Notes, Testing). Use `tmp_path` and explicit paths for `settings.load` / `settings.save`; use a fake key (`FAKE-KEY-123`); never touch the real `%APPDATA%` config.
- Docs: TASK-015 documents DPAPI storage at the "ctypes, current Windows user" level. Nothing in this task changes documented behaviour, so no doc change is needed here.
- Rules (CLAUDE.md): no UI code in core modules, no new dependencies, never print or log the key.

## Steps

1. Read `app/secret_store.py`, `app/screens/settings_screen.py` (`_persist`, `_save`, `_disconnect`, `_refresh_status`), `tests/test_settings_secret.py` and `tests/test_gemini.py:340-375`.
2. Add failing tests to `tests/test_settings_secret.py`: SEC-1 (`protect` and `settings.save` with a lone surrogate), SEC-2 (shared prototypes unchanged, win32 only), and CR-1 (three stub-self cases).
3. Fix SEC-1 in `protect`.
4. Refactor `secret_store` to use a module-level `DATA_BLOB` and private `WinDLL` handles with prototypes set once.
5. Make `_persist` return a bool and gate `_refresh_status` on it in `_save` / `_disconnect`.
6. Run every validation command and record exit codes and pass/skip counts in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` if:
- the change needs files outside `files_allowed` (for example `app/settings.py` or `app/ui.py`),
- private `ctypes.WinDLL` instances cannot be used for DPAPI in this environment (report it; do not fall back to the shared `windll` prototypes),
- an acceptance criterion is ambiguous, or
- a validation command cannot run in this environment.

Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-016.md` (see templates/handoff.md)

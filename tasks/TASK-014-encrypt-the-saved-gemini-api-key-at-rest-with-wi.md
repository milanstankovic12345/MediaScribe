---
id: TASK-014
title: Encrypt the saved Gemini API key at rest with Windows DPAPI
status: ready
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: []
files_allowed: ["app/settings.py", "app/secret_store.py", "tests/test_settings_secret.py", "app/screens/settings_screen.py"]
files_excluded: []
review: ["code", "security"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_settings_secret.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "new module app/secret_store.py (stdlib ctypes only, no new dependency) exposes protect(text: str) -> str and unprotect(token: str) -> str, using crypt32 CryptProtectData / CryptUnprotectData with CRYPTPROTECT_UI_FORBIDDEN, freeing output blobs with LocalFree; the token is base64 text; every failure (API returns false, bad base64, non-str input, non-Windows) raises secret_store.SecretStoreError, a subclass of OSError, whose message never contains the plaintext"
  - "SEC-1: after settings.save(cfg) with cfg[\"gemini_api_key\"] = KEY, the raw config file text does not contain KEY and has no \"gemini_api_key\" field, but has a \"gemini_api_key_enc\" string; settings.get_gemini_key(settings.load(path)) returns KEY (env var unset); tests cover this with a mocked protect/unprotect pair and with real DPAPI"
  - "migration: a legacy file {\"gemini_api_key\": KEY, \"model\": \"tiny\"} loads with cfg[\"gemini_api_key\"] == KEY; after settings.save(settings.load(path), path) the file has gemini_api_key_enc, no plaintext gemini_api_key, does not contain KEY, and still has \"model\": \"tiny\""
  - "decryption failure: when gemini_api_key_enc cannot be decrypted (unprotect raises SecretStoreError, the value is not valid base64, or the value is not a string such as 5), settings.load returns cfg[\"gemini_api_key\"] == \"\" and raises nothing; nothing printed (capsys) or raised contains the key; tests cover all three cases"
  - "env override: with GEMINI_API_KEY set, settings.get_gemini_key(settings.load(path)) returns the env value both for a decryptable saved key and when decryption fails"
  - "empty key: settings.save with gemini_api_key \"\" writes neither gemini_api_key nor gemini_api_key_enc and does not call protect; tests/test_core.py settings tests (roundtrip, defaults, per-screen dirs, gemini defaults) still pass unchanged"
  - "encryption failure: if protect raises SecretStoreError, settings.save raises OSError, the file on disk keeps its previous content, and the plaintext key is never written; the Settings screen's existing except OSError in _persist and App._close then handle it"
  - "settings.save does not mutate the dict it is given (the in-memory cfg keeps the plaintext gemini_api_key for this session and never holds gemini_api_key_enc after load), so app/screens/settings_screen.py, transcribe.py and get_gemini_key keep working with cfg[\"gemini_api_key\"]"
  - "real DPAPI test (skipped unless sys.platform == \"win32\"): unprotect(protect(KEY)) == KEY, KEY is not a substring of the token, a non-ASCII value (\"ključ-Ж\") round-trips, and unprotect of a valid-base64 non-DPAPI blob raises SecretStoreError; it runs offline"
  - "no test touches the network or writes outside tmp_path (pass explicit paths to load/save); full suite passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

Store the Gemini API key in `config.json` only as a Windows DPAPI-encrypted value, migrate an existing plaintext key on the next save, and treat an undecryptable key as unset, while the in-memory `cfg["gemini_api_key"]` and the `GEMINI_API_KEY` override keep working as now.

## Context

- Finding: `reports/reviews/TASK-008-security.md` SEC-1 (low, CWE-312): the key is stored in plaintext in `%APPDATA%\yt-tool\config.json` (`app/settings.py:50-54`, written from `app/screens/settings_screen.py:82-85`). Deferred in `tasks/TASK-011-harden-gemini-retries-fallback-redirects-and-mod.md`.
- **User decision (final):** encrypt with Windows DPAPI via `ctypes` (no new dependency); migrate a legacy plaintext key automatically on the next save; a decryption failure means the key is unset (no crash, key never logged); env `GEMINI_API_KEY` still overrides.
- Testing rules: `project-context/project-profile.md` (Notes, Testing). Use `tmp_path` and explicit `path` arguments to `settings.load` / `settings.save`; never touch the real `%APPDATA%` config. Use a fake key such as `FAKE-KEY-123`. `monkeypatch.delenv("GEMINI_API_KEY", raising=False)` in tests that assert the saved key. The real-DPAPI test is allowed because it is local and offline; mark it `pytest.mark.skipif(sys.platform != "win32", ...)`.
- **Design decisions:**
  - `app/secret_store.py` (new, UI-free): `DATA_BLOB` ctypes structure; `ctypes.windll.crypt32.CryptProtectData` / `CryptUnprotectData` with explicit `argtypes`/`restype`; flag `CRYPTPROTECT_UI_FORBIDDEN = 0x1`; free `pbData` of the output blob with `ctypes.windll.kernel32.LocalFree`. Encode text as UTF-8; the token is `base64.b64encode(blob).decode("ascii")`. An optional fixed app-specific entropy is allowed if both directions use the same module constant. `class SecretStoreError(OSError)`.
  - `app/settings.py`:
    - `load`: after merging the file into the defaults, `pop` `gemini_api_key_enc`. If it was present, set `gemini_api_key` to `unprotect(value)` on success, else `""` (catch `SecretStoreError`; a non-str value counts as a failure). If only a legacy plaintext `gemini_api_key` is present, keep it in memory as is. When `gemini_api_key_enc` decrypts, it wins over any plaintext field.
    - `save`: build a copy of `data`, pop `gemini_api_key` and `gemini_api_key_enc` from the copy, and if the key (stripped) is non-empty write `gemini_api_key_enc = protect(key)`. Call `protect` before opening the file, so an encryption failure raises (`SecretStoreError` is an `OSError`) with the file untouched.
    - `get_gemini_key` and `DEFAULTS["gemini_api_key"] = ""` stay as they are (`tests/test_core.py:159` checks the default; `tests/test_gemini.py:217` checks the env override on a plain dict).
  - No logging is added to `settings`; it has no logger, and the key must never be logged.
- `app/screens/settings_screen.py` is in scope only if a change turns out to be needed. With the design above it should not be: `_save` / `_disconnect` set `cfg["gemini_api_key"]` and call `settings.save`, and `_persist` already catches `OSError`. Showing a special "saved key could not be read" status is out of scope (the screen shows "Not connected").
- Callers of `settings.load` / `save`: `app/ui.py:23` (load), `app/ui.py:56` (`_close`, catches `OSError`), `app/screens/settings_screen.py:78` (`_persist`). `app/ui.py` is not in scope and needs no change.
- Documentation (techstack row, CLAUDE.md gotcha) is TASK-015, not this task.
- Rules (CLAUDE.md): no UI code in core modules; no new dependencies; never print or log the key.

## Steps

1. Read `app/settings.py`, `app/screens/settings_screen.py`, `app/ui.py` (load/save calls) and the settings tests in `tests/test_core.py`.
2. Write `tests/test_settings_secret.py` with failing tests: mocked round-trip (file has no plaintext key), legacy migration, decrypt failures (SecretStoreError, bad base64, non-str), env override, empty key, encryption failure leaves the file unchanged, input dict not mutated, and the Windows-only real DPAPI round-trip.
3. Implement `app/secret_store.py`.
4. Wire `protect` / `unprotect` into `settings.save` / `settings.load` as described.
5. Run every validation command and record the exit codes and pass/skip counts in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` if:
- the change needs files outside `files_allowed` (for example `app/ui.py`, `app/screens/transcribe.py` or `requirements.txt`),
- DPAPI cannot be called through `ctypes` in this environment and the real-DPAPI test cannot run (report it; do not fall back to plaintext or to a weaker scheme),
- an acceptance criterion is ambiguous, or
- a validation command cannot run in this environment.

Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-014.md` (see templates/handoff.md)

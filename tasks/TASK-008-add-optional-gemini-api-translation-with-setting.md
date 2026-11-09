---
id: TASK-008
title: Add optional Gemini API translation with Settings screen and connect guidance
status: ready
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-003", "TASK-006", "TASK-007", "TASK-010"]
files_allowed:
  - app/gemini.py
  - app/translator.py
  - app/settings.py
  - app/ui.py
  - app/screens/settings_screen.py
  - app/screens/transcribe.py
  - tests/test_gemini.py
  - tests/test_core.py
  - docs/techstack.md
  - docs/blueprint.md
  - docs/tasks.md
  - CLAUDE.md
files_excluded: []
review: ["code", "security"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_gemini.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
  - cmd: .venv/Scripts/python -c "import app.ui, app.screens.settings_screen"
    expect: exit 0
acceptance:
  - Sidebar has a Settings screen with a masked Gemini API key field, Show/Hide, Save, Test connection and Disconnect buttons, a 'Get a free API key' link that opens https://aistudio.google.com/apikey in the browser, and a one-line privacy note that transcript text is sent to Google
  - Test connection calls Gemini in a worker thread and reports Connected / Invalid key / No internet / Rate limited without freezing the UI
  - Transcribe screen has a 'Translator' menu with 'Local (NLLB, offline)' and 'Gemini (online, better context)'; choosing Gemini without a saved key shows inline guidance with 'Get API key' (opens the AI Studio page) and 'Open Settings' (switches to the Settings screen) and blocks Start with a clear message
  - after saving a key in Settings the Transcribe screen sees it without restarting the app
  - app/gemini.py translates the whole transcript in ordered chunks (with preceding lines as context) via urllib using structured JSON output, returns exactly one translation per input segment, and keeps every start/end time
  - a chunk whose response has missing/extra ids is retried once, then translated with local NLLB and logged
  - HTTP 429 is retried with backoff (max 3 tries); 400/401/403 raise a readable 'Gemini API key invalid or not allowed' error; network errors raise a readable error
  - the API key is sent only in the x-goog-api-key header, never in URLs, logs, error messages or the Done popup; env var GEMINI_API_KEY overrides the saved key
  - settings gain gemini_api_key='' and translator='Local (NLLB, offline)' defaults with tests; no new pip dependency
  - docs/techstack.md, docs/blueprint.md, docs/tasks.md and CLAUDE.md describe the Gemini option
max_retries: 2
attempts: 0
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Let the user connect a free Google Gemini API key in a new Settings screen and choose Gemini instead of local NLLB on the Transcribe screen, for subtitle translations that use the whole transcript as context.

## Context

Feature plan: `C:\Users\milla\.claude\plans\analyze-this-project-and-purrfect-flute.md` (section "Decision: translation backend", optional Gemini backend). Builds on TASK-003 (`app/translator.py`), TASK-006 (Transcribe screen subtitle options) and TASK-007 (docs); read their handoffs in `reports/handoffs/` first.

**Context sent to Gemini.** Gemini gets the transcript text, not the video file. "Whole-video context" means the full ordered transcript, sent in chunks of about 6000 characters. Each chunk includes the last ~5 source lines of the previous chunk, marked as context-only. Whisper keeps producing all the timing, so Gemini never changes start/end times.

**`app/gemini.py`** (new, UI-free, plain `cb` / `log` callbacks, standard library only: `urllib.request`, `json`):
- `API_KEY_URL = "https://aistudio.google.com/apikey"`.
- `MODEL`: a module constant. Before setting it, check the current Gemini API docs for a model on the free tier (for example a "flash" model), and name the source in the handoff. Allow an optional `gemini_model` settings override.
- Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`, with header `x-goog-api-key: <key>` and a 60 s timeout.
- Request: `generationConfig.responseMimeType = "application/json"` plus a `responseSchema` for an array of `{i: integer, t: string}`. The system instruction says: translate each item into <target language name>, keep the meaning and tone, keep the same ids, return exactly one item per id, don't merge or split items, and treat the context lines as read-only.
- `check_key(key) -> None`: makes a tiny request and raises `GeminiError` with a kind of `invalid_key`, `rate_limited`, `network` or `other`.
- `translate_segments(segments, target_label, key, cb=None, log=None, fallback=None) -> list[Segment]`: uses the same target labels as `translator.TARGETS`. "Serbian (Latin)" asks Gemini for Serbian in Latin script directly, with no transliteration.
- Validation: if a chunk comes back with missing or extra ids, retry it once. If it still fails, call `fallback(chunk)` (local NLLB) and log it.
- 429: back off (use `retryDelay` if the response includes one, otherwise 5 s / 15 s / 30 s), max 3 tries. 400/401/403 raise "Gemini API key invalid or not allowed". URLError and timeouts raise "Cannot reach Gemini (check internet connection)".
- Never put the key in a URL, a log line, an exception message or `repr`.

**`app/translator.py`**: add `ENGINES = ["Local (NLLB, offline)", "Gemini (online, better context)"]` and a `translate(segments, src_iso, target_label, engine, api_key, cb, log)` dispatcher. With Gemini it calls `gemini.translate_segments`, passing local NLLB as the fallback.

**Settings:**
- `app/settings.py`: add `DEFAULTS` `gemini_api_key=""` and `translator="Local (NLLB, offline)"`.
- Add `get_gemini_key(cfg)`, which returns `os.environ["GEMINI_API_KEY"]` if set, otherwise `cfg["gemini_api_key"]`.
- The key is stored in the existing `%APPDATA%\yt-tool\config.json`, which is per-user. Using `keyring` would add a dependency, so don't.

**`app/screens/settings_screen.py`** (new): a plain `ctk.CTkFrame`, not the `Screen` base class.
- It has a "Gemini API (optional)" section:
  - a masked `CTkEntry(show="*")`, with Show/Hide,
  - Save (writes `cfg["gemini_api_key"]` and calls `settings.save`),
  - Test connection (runs `gemini.check_key` in a thread, sends the result back through a `queue.Queue` polled with `after(100)`, and shows it in a status label),
  - Disconnect (clears the key),
  - a status line: "Connected", "Not connected", or "Using GEMINI_API_KEY from environment",
  - step-by-step guidance: 1) open Google AI Studio, 2) sign in, 3) "Create API key", 4) paste it here and click Save. The link button calls `webbrowser.open(gemini.API_KEY_URL)`.
  - A privacy note: transcript text is sent to Google, and free-tier data may be used by Google to improve its products, so don't use it for confidential recordings.
- Implement `collect_cfg()` so `App._close` keeps working.

**`app/ui.py`:** add `("settings", "Settings", SettingsScreen)` to `NAV` as the last item. In `show(key)`, call `screen.on_show()` if the screen has that method, so the Transcribe screen re-checks the key when the user returns to it.

**`app/screens/transcribe.py`:** add a `Translator:` `CTkOptionMenu(values=translator.ENGINES)` to the subtitle row.
- If Gemini is selected and `settings.get_gemini_key(self.cfg)` is empty, show an inline guidance frame: "Gemini is not connected. Get a free API key, then paste it in Settings." It has two buttons:
  - [Get API key], which calls `webbrowser.open`,
  - [Open Settings], which calls `self.master.show("settings")`.
- `_validate` blocks Start with that message.
- The key is captured in `_args()` on the main thread and passed to the worker. It is never logged.

**Tests** go in the new `tests/test_gemini.py`. Monkeypatch `urllib.request.urlopen` with fake responses, and never call the network. Cover:
- the request shape: the key is in the header, not in the URL,
- chunking and timestamps preserved,
- a bad-id retry, then the fallback,
- 429 backoff (monkeypatch `time.sleep`),
- invalid key and network errors, and that no error text contains the key,
- the `GEMINI_API_KEY` env override.

Put the settings default tests in `tests/test_core.py`.

**Rules (CLAUDE.md):** no UI code in core modules; never touch widgets off the main thread; no new dependencies; personal use only.

## Steps

1. Read the TASK-003/006/007 handoffs and the current `translator.py` and `transcribe.py`.
2. Write failing tests in `tests/test_gemini.py` and the settings tests in `tests/test_core.py`.
3. Implement `app/gemini.py`, then the `translator.translate` dispatcher and the settings helpers.
4. Add `SettingsScreen` and the `ui.py` navigation plus the `on_show` hook.
5. Add the Translator menu, the not-connected guidance and validation to the Transcribe screen.
6. Update `docs/techstack.md` (Gemini via REST and urllib, no new dependency, optional, free tier, privacy note), `docs/blueprint.md` (module map and flow), `docs/tasks.md` (Round 4 item) and `CLAUDE.md` (the Gotchas section on API key handling and the env override).
7. Run every validation command. If a display is available, start the app and check the Settings screen, the guidance, and the link opening. Record what was checked, or say it was not checked.

## Blockers

Stop and write a handoff with `status: blocked` if:
- the change needs files outside `files_allowed`,
- no Gemini model on the free tier can be confirmed from current docs,
- an acceptance criterion is ambiguous, or
- a validation command cannot run in this environment.

Never widen scope silently. Never commit a real API key or put one in tests.

## Deliverables

- Code/tests/docs within `files_allowed`
- `reports/handoffs/TASK-008.md` (see templates/handoff.md)

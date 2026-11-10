---
task: TASK-008
agent: implementer
model: claude-sonnet-5-5
attempt: 1
status: done_with_concerns
summary: Added optional Gemini translation (app/gemini.py), translator.translate dispatcher, Settings screen, Translator menu with not-connected guidance, settings helpers, tests and docs.
files_modified:
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
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_gemini.py -q
    exit_code: 0
    summary: 24 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 123 passed, 2 skipped
  - cmd: .venv/Scripts/python -c "import app.ui, app.screens.settings_screen"
    exit_code: 0
    summary: imports ok
unresolved:
  - Link opening, Test connection against the real API and visual layout were not checked (no real key, no screenshot).
risks:
  - 400 is mapped to invalid-key per the task, so a genuinely malformed request also reads as invalid key.
  - tests/, docs/ and CLAUDE.md are gitignored, so those edits will not show in git status/diff.
decisions:
  - MODEL = gemini-3.5-flash-lite, free tier and described as optimized for translation on https://ai.google.dev/gemini-api/docs/pricing (gemini-2.5-flash is listed there as deprecated). Optional cfg gemini_model override.
  - _run gained trailing optional args engine, api_key, gemini_model so existing transcribe tests stay valid; local engine still calls translator.translate_segments directly.
  - _validate uses getattr(self, "engine", None) so existing stub-based tests keep working.
  - Translator menu sits in its own row; guidance shown only when Subtitles ticked, Gemini chosen, target not Original and no key.
next_steps:
  - Manual check with a real key (Test connection, link, one translation run).
blocker: null
---

## What changed
New app/gemini.py, app/screens/settings_screen.py, tests/test_gemini.py; edits to translator, settings, ui (Settings nav, on_show hook), transcribe screen, docs.

## Evidence
All three validation commands exit 0. Headless Tk smoke: App builds, guidance frame is mapped with Gemini and no key, hidden after the key is set and the screen is re-shown.

## Notes for the next session
Key travels only in the x-goog-api-key header; errors are fixed strings.

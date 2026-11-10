---
task: TASK-011
agent: implementer
model: claude-sonnet-5-5
attempt: 1
status: done
summary: Hardened Gemini (no-text and bad-id replies are mismatches, no-redirect opener, 5xx backoff, model-name check) and fixed the Settings env-key test, the target-menu guidance command and added the Gemini _run test.
files_modified:
  - app/gemini.py
  - app/screens/transcribe.py
  - app/screens/settings_screen.py
  - tests/test_gemini.py
  - tests/test_transcribe_screen.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_gemini.py -q
    exit_code: 0
    summary: 41 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 141 passed, 2 skipped
unresolved: []
risks:
  - CR-3 command is a code check only, not visually verified
decisions:
  - Ids must be exactly int (type check), so floats, strings and Infinity are mismatches
  - Requests go through gemini._open (module opener with refusing redirect handler); tests patch it
next_steps:
  - SEC-1 plaintext key in config.json (DPAPI) still open, needs its own task
  - CR-6 Gemini called when source equals target / unsupported NLLB source in fallback (app/translator.py) still open
  - Optional doc line in docs/CLAUDE.md for redirect refusal and 5xx retry
blocker: null
---

## What changed
See summary; all CR-1..5 and SEC-2..4 criteria implemented with tests.
## Evidence
Both validation commands exit 0.
## Notes for the next session
Deferred items listed in next_steps.

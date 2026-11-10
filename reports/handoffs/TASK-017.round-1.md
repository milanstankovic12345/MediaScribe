---
task: TASK-017
agent: implementer
model: claude-sonnet-5-5
attempt: 0
status: blocked
summary: Implemented _source_file, URL-wins _validate/_args, URL clearing in _pick_file and _on_url_change binding with tests; the full suite has one failure in tests/test_gemini.py (out of scope) caused by _validate now calling self._source_file on its stub.
files_modified:
  - app/screens/transcribe.py
  - tests/test_transcribe_screen.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q
    exit_code: 0
    summary: 52 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 1
    summary: "1 failed (test_gemini.py test_validate_blocks_gemini_without_key), 180 passed, 2 skipped"
unresolved:
  - "test_gemini.py test_validate_blocks_gemini_without_key builds a stub without _source_file; add _source_file lambda to it (file outside files_allowed)"
risks: []
decisions:
  - Left the implementation as specified (_validate calls self._source_file) rather than working around the stub in production code.
next_steps:
  - Widen files_allowed to include tests/test_gemini.py (one-line stub fix), or approve it, then re-run the full suite.
blocker: Full-suite validation fails only because tests/test_gemini.py (outside files_allowed) needs a one-line stub update.
---

## What changed
transcribe.py: added _source_file and _on_url_change (bound to KeyRelease and Paste via after_idle), _validate and _args use _source_file, _pick_file clears the URL. Tests updated and added in test_transcribe_screen.py (make_stub now provides _source_file).

## Evidence
Targeted tests 52 passed; full suite 1 failure as above.

## Notes for the next session
Fix the stub in tests/test_gemini.py line ~230.

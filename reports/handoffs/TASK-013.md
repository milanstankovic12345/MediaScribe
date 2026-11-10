---
task: TASK-013
agent: implementer
model: claude-sonnet-5-5
attempt: 1
status: done
summary: translate() now routes same-language targets to local translate_segments (no Gemini, no model), and the Gemini per-chunk fallback keeps original text with a log line when NLLB lacks the source.
files_modified:
  - app/translator.py
  - tests/test_translator.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_translator.py -q
    exit_code: 0
    summary: 21 passed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 157 passed, 2 skipped
unresolved: []
risks: []
decisions: []
next_steps: []
blocker: null
---

## What changed
translate(): same-language shortcut and inner fallback function. 9 new tests (parametrized) in tests/test_translator.py.
## Evidence
Both validation commands exit 0.
## Notes for the next session
None.

---
task: TASK-007
agent: docs-writer
model: claude-haiku-5-5
attempt: 0
status: done_with_concerns
summary: "Documented the subtitles and translation feature as built in docs/techstack.md, docs/blueprint.md, docs/prd.md, docs/tasks.md (Round 4) and CLAUDE.md (Commands, Architecture, Gotchas, test files). Validation pytest exits 0 with 98 passed and 2 skipped. Concerns: docs, tests and CLAUDE.md are gitignored and untracked, and sentencepiece is not installed in .venv, so the real NLLB path has not run."
files_modified:
  - docs/techstack.md
  - docs/blueprint.md
  - docs/prd.md
  - docs/tasks.md
  - CLAUDE.md
tests:
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: "98 passed, 2 skipped (validation command, run after all edits)"
  - cmd: .venv/Scripts/python -m pytest tests/test_core.py::test_safe_name
    exit_code: 0
    summary: "1 passed (single-test command documented in CLAUDE.md)"
  - cmd: YT_TOOL_E2E=1 .venv/Scripts/python -m pytest tests/test_e2e_subtitles.py -q
    exit_code: 0
    summary: "2 passed with real ffmpeg 9.0.2 (bash env syntax)"
  - cmd: powershell -NoProfile -Command "$env:YT_TOOL_E2E='1'; .venv\Scripts\python -m pytest tests/test_e2e_subtitles.py -q"
    exit_code: 0
    summary: "2 passed (PowerShell form documented in CLAUDE.md)"
  - cmd: .venv/Scripts/python -m pytest --collect-only -q
    exit_code: 0
    summary: "100 tests collected across test_core, test_subtitles, test_translator, test_transcribe_screen, test_e2e_subtitles"
  - cmd: PYTHONIOENCODING=utf-8 .venv/Scripts/python -c "from app.translator import cyr_to_lat ..."
    exit_code: 0
    summary: "cyr_to_lat gives Ljubav i đak; MODEL_REPO and MODEL_REVISION match docs; fmt_srt_time(3725.5) gives 01:02:05,500; every LANGUAGES entry maps to an NLLB code"
unresolved:
  - "run.bat and .venv/Scripts/python main.py (existing Commands lines, not changed) were not executed because they launch the GUI. Not verified in this session."
  - "The real NLLB path (model download, tokenizer, CTranslate2 inference) is not verified: import sentencepiece fails in .venv with ModuleNotFoundError and the tests use fakes. Docs describe what the code does, not that it runs end to end."
  - "Subtitles UI was not launched or visually verified (see TASK-006 handoff). tasks.md item 28 stays unticked for this."
  - "CLAUDE.md, docs/ and tests/ are listed in .gitignore and are not tracked by git (git ls-files lists none of them). These doc edits and the test files will not be committed unless .gitignore changes or the files are force-added. Decision needed from the orchestrator or user; not changed here."
risks:
  - "The CC-BY-NC licence statement for NLLB comes from the task brief and plan and was not re-checked against upstream in this session."
  - "The model size (about 600 MB, from the plan) is not stated in the docs because it was not measured."
decisions:
  - "Ticked tasks.md Round 4 items 20-27 (TASK-002 to TASK-010 done, plus this docs task). Item 28 (manual UI e2e) left open."
  - "prd.md: removed SRT export from Out of scope because it is now built. Gemini is mentioned only as planned (TASK-008, status ready, not built)."
  - "README.md not touched, as the task requires."
  - "Documented embed output as .mp4 only, because the screen always writes .mp4. The .mkv codec branch in subtitles.embed is not exposed in the UI and is not documented as a user feature."
next_steps:
  - "Orchestrator: decide how to handle the .gitignore entries for CLAUDE.md, docs/ and tests/ so the docs and new test files can be committed."
  - "Orchestrator: install sentencepiece into .venv (pip install -r requirements.txt) and run one real translation to verify the NLLB path, if the user wants that verified."
  - "Manual UI check of the Subtitles row via run.bat remains open (tasks.md item 28)."
blocker: null
---

## What changed
- docs/techstack.md: Translation row (NLLB-200 distilled 600M via CTranslate2, pinned repo, sentencepiece as the only new package, local/free/offline, CC-BY-NC note, Serbian transliteration) and Subtitles row (SRT UTF-8 BOM, ffmpeg already required).
- docs/blueprint.md: module map gains app/translator.py and app/subtitles.py; test file list updated; new subtitles data flow (translate, to_cues, write_srt, optional embed or burn, URL video download); Transcribe progress split.
- docs/prd.md: subtitles feature paragraph under Requirements; SRT export removed from Out of scope; Gemini option noted as planned only.
- docs/tasks.md: new Round 4 (subtitles) section; items 20-27 ticked (TASK-002, 003, 004, 005, 006, 009, 010, 007); item 28 (manual UI e2e) unticked.
- CLAUDE.md: Commands (opt-in e2e command, ffmpeg use for subtitles); Architecture (core module list, subtitle pipeline, test files); Gotchas (translator module state and shared _cuda_broken, model repo and revision, sentencepiece requirement, Serbian Latin transliteration, burn subs.srt and cwd workaround, SRT BOM, test and e2e rules). Tests bullet updated.
- README.md, app code and tests not touched.

## Evidence
See the tests list. Every documented command was run in this session except the two Commands lines that launch the GUI (run.bat, main.py), which are listed as unverified.

## Notes for the next session
- Git: git ls-files lists none of CLAUDE.md, docs/ or tests/, and .gitignore excludes them. git status therefore shows only reports/ and the task file as modified.
- The .venv has ctranslate2 4.8.3 and huggingface_hub 2.2.0 but no sentencepiece. Real translation has never run here.
- tasks/TASK-007 and other tasks/*.md files were not edited.

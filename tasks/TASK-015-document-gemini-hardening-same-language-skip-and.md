---
id: TASK-015
title: Document Gemini hardening, same-language skip and DPAPI key storage
status: ready
agent: docs-writer
skills: []
model_tier: fast
priority: p2
depends_on: ["TASK-012", "TASK-013", "TASK-014"]
files_allowed: ["CLAUDE.md", "docs/blueprint.md", "docs/techstack.md"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -c "import pathlib,sys; t=[pathlib.Path(p).read_text(encoding='utf-8') for p in ('CLAUDE.md','docs/blueprint.md','docs/techstack.md')]; sys.exit(int('urlopen' in t[0] or 'gemini._open' not in t[0] or not all('DPAPI' in x for x in t)))"
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "CR-2 doc part: the CLAUDE.md Gemini gotcha (currently line 37) no longer says tests mock urlopen; it says tests/test_gemini.py fakes gemini._open (requests go through a module opener that refuses redirects), and the word urlopen no longer appears in CLAUDE.md"
  - "CLAUDE.md, docs/blueprint.md (gemini.py module-map line, currently line 11, which says only \"429 backoff\") and the Gemini row of docs/techstack.md state the behaviour as built: HTTP 429/500/502/503/504 are retried with backoff (retryDelay if given, at most 3 requests), 3xx redirects are refused so the key header never follows a Location, and an invalid or non-string gemini_model falls back to gemini.MODEL"
  - "CLAUDE.md and docs/blueprint.md (translation data flow, currently line 24) say that with the Gemini engine a same-language source/target skips Gemini (Serbian (Latin) still transliterates locally), and that a failed chunk whose source language NLLB does not support keeps its original text with a log line instead of aborting"
  - "DPAPI storage is documented in all three files: CLAUDE.md Gemini gotcha says the key is saved only as the DPAPI-encrypted gemini_api_key_enc in config.json (app/secret_store.py, ctypes, current Windows user), a legacy plaintext gemini_api_key is migrated on the next save, an undecryptable value is treated as unset, and env GEMINI_API_KEY still overrides; docs/blueprint.md lists app/secret_store.py in the module map; docs/techstack.md notes DPAPI via ctypes (standard library, no new dependency)"
  - "the CLAUDE.md Architecture test-file list mentions tests/test_gemini.py and tests/test_settings_secret.py (the real-DPAPI test runs only on Windows)"
  - "only behaviour that exists in the code and in reports/handoffs/TASK-012.md, TASK-013.md and TASK-014.md is documented; README.md, docs/prd.md and docs/tasks.md are not touched; the validation check exits 0 and the full suite still passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

Update `CLAUDE.md`, `docs/blueprint.md` and `docs/techstack.md` so they describe the Gemini retry/redirect/model-name hardening, the translator same-language skip and unsupported-source fallback, and DPAPI key storage exactly as built in TASK-012..014.

## Context

- Findings routed here: `reports/reviews/TASK-011-code.md` CR-2 (`CLAUDE.md:37` still says "Tests mock `urlopen`"), and the doc follow-ups listed in the handoffs `reports/handoffs/TASK-011.md`, `TASK-012.md`, `TASK-013.md` and `TASK-014.md` (`next_steps`). Read those handoffs and the final code first: `app/gemini.py` (`_post`, `_NoRedirect`, `_open`), `app/translator.py` (`translate`), `app/settings.py` (`load`, `save`), `app/secret_store.py`.
- Current text to update:
  - `CLAUDE.md:37`: the Gemini gotcha (key location `config.json` `gemini_api_key`, env override, header-only key, "Tests mock `urlopen`").
  - `CLAUDE.md` Architecture "Test files" bullet (lists test_core, test_subtitles, test_translator, test_transcribe_screen, test_e2e_subtitles) and the Gotchas "Tests" bullet.
  - `docs/blueprint.md:11-12` (module map: gemini.py "429 backoff", settings_screen.py) and `:24` (translation data flow).
  - `docs/techstack.md:11` (Gemini row).
- Style precedent: `tasks/TASK-007-document-subtitles-feature-in-docs-and-claude-md.md` (same docs-writer task type). Keep CLAUDE.md lines terse, in the existing style; no emojis.
- The validation `python -c` check fails if `urlopen` still appears in `CLAUDE.md`, if `gemini._open` is missing from it, or if any of the three files lacks the word `DPAPI`.
- `tests/` and `docs/` are listed in `.gitignore` (a deliberate project choice); that is not something to change here.
- Do not touch README.md, `docs/prd.md` or `docs/tasks.md` (not in scope).

## Steps

1. Read the TASK-012..014 handoffs and the final code listed above.
2. Update the CLAUDE.md Gemini gotcha, the test-file list and, if needed, the Tests gotcha bullet.
3. Update the `docs/blueprint.md` module map (gemini.py retries/redirects, new `app/secret_store.py`, settings key storage) and the translation data flow.
4. Update the `docs/techstack.md` Gemini row (retries, redirects) and add DPAPI key storage via `ctypes` (no new dependency).
5. Run every validation command and record the exit codes in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` if:
- any of TASK-012, TASK-013 or TASK-014 is not done, or its handoff contradicts the acceptance criteria here (document what was built and list the mismatch),
- the change needs files outside `files_allowed`, or
- a validation command cannot run in this environment.

Never widen scope silently.

## Deliverables

- Doc changes within `files_allowed`
- `reports/handoffs/TASK-015.md` (see templates/handoff.md)

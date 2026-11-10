---
id: TASK-020
title: Document the Open folder Done dialog and the split Transcribe / Translate buttons
status: done
agent: docs-writer
skills: []
model_tier: fast
priority: p2
depends_on: ["TASK-018", "TASK-019"]
files_allowed: ["CLAUDE.md", "docs/blueprint.md", "docs/tasks.md"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -c "import pathlib,sys; c=pathlib.Path('CLAUDE.md').read_text(encoding='utf-8'); b=pathlib.Path('docs/blueprint.md').read_text(encoding='utf-8'); sys.exit(int(not ('done_dialog' in c and 'done_dialog' in b and 'Open folder' in c and 'Open folder' in b and 'action_buttons' in b)))"
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "docs/blueprint.md module map lists app/screens/done_dialog.py (done_payload, open_folder, DoneDialog with an Open folder button that opens Explorer with the new file selected, or the playlist folder)"
  - "docs/blueprint.md Threading paragraph says (\"done\", ...) now carries (message, path) (a plain str is still accepted and shows no Open folder button), and the playlist worker sends the playlist folder as the path"
  - "docs/blueprint.md transcribe data flow, Subtitles note and UI layout say the Transcribe screen has two buttons as built in TASK-019 (labels as in the code): one writes Markdown/PDF only, the other runs translation, SRT and embed/burn; the old \"Subtitles checkbox\" wording and the sentence that subtitles and MD/PDF can be ticked in any combination are updated to match the code; the base class hook (_build_actions / action_buttons) is mentioned in the app/screens line"
  - "CLAUDE.md Architecture bullets (worker-to-UI communication, Subtitles, Test files) describe the (message, path) done payload, the DoneDialog Open folder button, the two Transcribe buttons and tests/test_done_dialog.py, in the existing terse style and without emojis"
  - "docs/tasks.md gets a new round with two ticked items for TASK-018 and TASK-019 (next free item numbers after 29); existing items are unchanged"
  - "only behaviour that exists in the code and in reports/handoffs/TASK-018.md and TASK-019.md is documented; README.md, docs/prd.md and docs/techstack.md are not touched; the validation check exits 0 and the full suite still passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

Update `CLAUDE.md`, `docs/blueprint.md` and `docs/tasks.md` so they describe the Done dialog's Open folder button and the two-button Transcribe screen exactly as built in TASK-018 and TASK-019.

## Context

- CLAUDE.md requires an update to `docs/blueprint.md` when module boundaries or data flow change. TASK-018 adds a module (`app/screens/done_dialog.py`) and changes the `("done", ...)` payload. TASK-019 changes the Transcribe screen's flow (two buttons, no Subtitles checkbox if Q4 was answered yes).
- Read first: `reports/handoffs/TASK-018.md`, `reports/handoffs/TASK-019.md` (including the answers to the TASK-019 open questions recorded in that task's Context), and the final code in `app/screens/done_dialog.py`, `app/screens/base.py` and `app/screens/transcribe.py`.
- Text to update:
  - `docs/blueprint.md`: module map (`app/screens/` line), "Data flow (transcribe, subtitles)", "Subtitles and MD/PDF are independent..." sentence, "UI layout" and "Threading" paragraphs.
  - `CLAUDE.md`: Architecture bullets "Worker-to-UI communication", "Subtitles (same screen, `TranscribeScreen._run`)" and "Test files".
  - `docs/tasks.md`: append a round with ticked items for TASK-018 and TASK-019.
- The validation `python -c` check fails unless `done_dialog` and `Open folder` appear in both CLAUDE.md and blueprint.md and `action_buttons` appears in blueprint.md. If TASK-019 was built without an `action_buttons` name, stop with `blocked` and report the mismatch; do not invent the name.
- Style precedent: `tasks/TASK-015-document-gemini-hardening-same-language-skip-and.md`. `tests/` and `docs/` are gitignored by project choice; that is not something to change.

## Steps

1. Read the TASK-018 and TASK-019 handoffs and the final code listed above.
2. Update the `docs/blueprint.md` sections listed above.
3. Update the CLAUDE.md Architecture bullets.
4. Append the ticked items to `docs/tasks.md`.
5. Run every validation command and record the exit codes in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` if TASK-018 or TASK-019 is not done, if its handoff contradicts the acceptance criteria here (document what was built and list the mismatch), if the change needs files outside `files_allowed`, or if a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Doc changes within `files_allowed`
- `reports/handoffs/TASK-020.md` (see templates/handoff.md)

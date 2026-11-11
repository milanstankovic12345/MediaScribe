---
task: TASK-025
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - CLAUDE.md (diff vs scratchpad TASK-025-base/CLAUDE.md)
  - docs/blueprint.md (diff vs TASK-025-base/blueprint.md)
  - docs/tasks.md (diff vs TASK-025-base/tasks.md)
  - app/transcript_import.py (full)
  - app/exporter.py (full)
  - app/screens/transcribe.py (full, working tree incl. TASK-024 changes)
  - app/settings.py (sub_doc default)
  - app/transcriber.py LANGUAGES, app/translator.py WHISPER_TO_NLLB and translate()
  - reports/handoffs/TASK-022.md, TASK-023.md, TASK-024.md, reports/handoffs/TASK-025.md
  - reports/reviews/TASK-024-code.md
  - tasks/TASK-020..TASK-024 titles and status
not_checked:
  - Runtime execution of the documented transcript-input behaviours (the read-only guard blocked a scratch script that writes temp files); verified by reading the code only
  - reports/handoffs/TASK-021.md body (title and tasks.md wording checked only)
  - Content of docs/prd.md, docs/techstack.md, README.md (only mtimes checked to confirm they were not touched)
findings:
  - id: CR-1
    severity: low
    title: Blueprint says "UTF-8 with BOM" for transcript decoding; the code accepts UTF-8 with or without BOM
    location: docs/blueprint.md:17
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: info
    title: The "Translated from" line is also omitted when the source language is unknown (Gemini + transcript without language); docs only name "Original"
    location: docs/blueprint.md:30
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: CLAUDE.md Gotchas "Tests:" list still omits test_done_dialog.py (pre-existing; the line was edited in this task)
    location: CLAUDE.md:42
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - "UTF-8 with BOM" reads as a requirement (Low, confidence 85)

- **Location:** `docs/blueprint.md:17` (module map line for `app/transcript_import.py`).
- **Impact:** A reader may think a BOM-less UTF-8 file falls through to cp1250. The code (`transcript_import._decode`, line 99) uses `data.decode("utf-8-sig")`, which accepts UTF-8 with or without a BOM. CLAUDE.md already words it correctly ("UTF-8 (BOM ok)"), so the two docs disagree slightly.
- **Reproduction:** Read blueprint line 17, then `app/transcript_import.py:97-104`: a plain UTF-8 file decodes on the first try.
- **Recommended fix:** Change to "UTF-8 (BOM optional), then cp1250, else an error".

### CR-2 - "Translated from" line also absent for an unknown source (Info, confidence 90)

- **Location:** `docs/blueprint.md:30`; same wording in `CLAUDE.md:25` ("none for "Original"").
- **Impact:** Docs are incomplete, not wrong. With Gemini and a transcript whose language is unknown, `t.language` is `""`, `src_lang = ""` (`transcribe.py:273`), and `exporter.to_markdown` / `write_pdf` skip the line because of `if translated_from:` (`exporter.py:22`, `71`).
- **Reproduction:** `Talk.xx.srt` (no recognised suffix), Language menu Auto, engine Gemini, target German, Translated document + Markdown ticked: `Talk.xx.de.md` has no "Translated from" line.
- **Recommended fix:** Optional: "for "Original" or an unknown source language there is no such line".

### CR-3 - Tests gotcha list omits test_done_dialog.py (Info, confidence 95)

- **Location:** `CLAUDE.md:42`.
- **Impact:** Pre-existing omission (base snapshot lacks it too). This task edited the line to add `test_transcript_import.py` but left the gap. The Architecture "Test files" bullet does list it, so nothing is lost.
- **Recommended fix:** Add `test_done_dialog.py` to the list when next touched.

## Verification of documented behaviour (all confirmed against the code)

- Module map: `transcript_import` exposes `parse_srt`, `parse_markdown`, `load` returning `(Transcript, title)`; `MAX_BYTES` = 20 MiB; language from the Markdown `- Language:` line, else the `<name>.<code>` suffix (`load` lines 117-127). Exporter `translated_from` adds "Translated from: <lang>" in MD and PDF.
- Translate / Subtitles: `_args` sets md/pdf to False when `subs`, so no source MD/PDF; `sub_doc` is a tuple of ticked formats; translated doc is written before the SRT (`_run` 271-280); `src_lang` is None for Original; `_validate` requires MD or PDF when the checkbox is ticked (line 179); `sub_doc` default False in settings.
- Transcript input: Transcribe refuses it (`_validate` 167, `_run` 223); Embed/Burn refused by `_validate` 172 because `.srt`/`.md` are not in `VIDEO_EXTS`; Language menu (non-Auto, not None) overrides (`_run` 226); `_clean_lang` maps `sr-Latn` to `sr` and keeps only the 13 codes of `LANGUAGES`/`WHISPER_TO_NLLB` (identical sets, so "language list" is accurate); unknown + local + non-Original raises `UNKNOWN_LANG_MSG` before translation; Gemini with unknown source goes to `gemini.translate_segments` (`translator.translate` 172 does not short-circuit when `src` is None); Original with unknown language yields `und`; title is the `# ` heading or the stem without language suffix; the overwrite guard runs after translation and before any write (matches TASK-024 review CR-1, documented honestly).
- UI layout: the Translated document checkbox sits in the Translate to / Video row (`_build_options` 88-90).
- tasks.md: items 32-35 added under Round 6, ticked, titles match TASK-021..024; items 1-31 unchanged (diff shows additions only). TASK-020..024 are all `done`.
- Two corrected stale statements (MD/PDF "ignored" in Translate / Subtitles; "subtitles, if ticked" for local file) are correct given TASK-019/022 behaviour.
- No emojis added; README.md (2026-10-29), docs/prd.md (2026-11-09), docs/techstack.md (2026-11-10) have mtimes before this task, so they were not touched.

## Validation commands (re-run by reviewer)

- `.venv/Scripts/python -c "...keyword check..."` -> exit 0
- `.venv/Scripts/python -m pytest -q` -> exit 0, 243 passed, 2 skipped (matches the handoff)

## Coverage statement

Inspected: the full diffs of the three edited docs against the pre-edit snapshot, and every documented claim against `app/transcript_import.py`, `app/exporter.py`, `app/screens/transcribe.py` (working tree), `app/settings.py`, `app/translator.py` and `app/transcriber.py`; handoffs TASK-022..025 frontmatter and the TASK-024 code review. Ran both validation commands. Not done: a runtime exercise of `_run` on a transcript (blocked by the read-only guard because it writes temp files), so behaviour claims are verified by code reading only (straight-line code, high confidence); TASK-021 handoff body not read beyond its title; prd/techstack/README content not diffed (mtime check only). No findings does not prove the docs are complete.

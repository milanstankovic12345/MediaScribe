---
id: TASK-022
title: Write a translated Markdown/PDF transcript from the Translate / Subtitles action
status: draft
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-021"]
files_allowed: ["app/exporter.py", "app/screens/transcribe.py", "app/settings.py", "tests/test_core.py", "tests/test_transcribe_screen.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_core.py tests/test_transcribe_screen.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "exporter.to_markdown, write_markdown and write_pdf accept a keyword translated_from: str | None = None; with None the Markdown text is byte-identical to today (existing test_markdown/test_pdf pass unchanged); with \"en\" the Markdown header has the line \"- Translated from: en\" directly after \"- Language: ...\" and the PDF header block has \"Translated from: en\" after the Language line"
  - "settings.DEFAULTS has \"sub_doc\": False and settings.load of a missing file returns it (asserted in tests/test_core.py)"
  - "The Transcribe screen has a \"Translated document\" checkbox in the Translate to row bound to self.sub_doc_var (initial value cfg[\"sub_doc\"]); collect_cfg writes \"sub_doc\""
  - "TranscribeScreen._args() returns a 12th element sub_doc: in subtitles mode with the checkbox ticked it is a tuple of the ticked formats in the order (\".md\", \".pdf\") (MD+PDF -> (\".md\", \".pdf\"), PDF only -> (\".pdf\",)); with the checkbox unticked, or in transcribe mode, it is (); md and pdf (elements 2 and 3) stay False in subtitles mode as before; the full-tuple tests from TASK-021 are extended to 12 elements"
  - "TranscribeScreen._validate in subtitles mode with the checkbox ticked and neither Markdown nor PDF ticked returns \"Tick Markdown and/or PDF for the translated document.\"; all other existing _validate messages and orders are unchanged"
  - "TranscribeScreen._run(..., subs=True, target=\"German\", sub_doc=(\".md\", \".pdf\")) translates once, then calls exporter.write_markdown and write_pdf with a Transcript whose segments are the translated segments (the same list later passed to subtitles.to_cues) and language \"de\", paths <out>/<safe title>.de.md and .de.pdf, and translated_from=\"en\"; the saved list order is [md, pdf, srt, video?] so the returned path is still the SRT or the embedded/burned video"
  - "With target Original and sub_doc=(\".md\",) _run writes <title>.<detected lang>.md with translated_from=None and never calls the translator; with sub_doc=() no exporter function is called in subtitles mode"
  - "_run keeps sub_doc as a trailing keyword parameter with default (), every existing _run test passes unchanged (the original-transcript calls to write_markdown/write_pdf keep their current 4 positional arguments), progress stays monotonic, the Gemini key never appears in the returned text, and no new dependency is added"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

"Translate / Subtitles" can also save the transcript in the target language as Markdown and/or PDF, next to the SRT, from the same translated segments.

## Context

Source of the request: Q2 in `tasks/TASK-019-split-the-transcribe-screen-action-into-separate.md` (answered "follow-up task"). Today translation feeds only the SRT: see `TranscribeScreen._run` in `app/screens/transcribe.py` (the `if subs:` block) and `app/exporter.py`.

OPEN QUESTIONS (task stays `draft` until a human answers; the acceptance criteria assume the recommended answers):

- Q2a. How is the translated document switched on? Recommended: a "Translated document" checkbox in the Translate to row (saved as `sub_doc`). Its formats come from the existing Markdown/PDF checkboxes. This is consistent with the TASK-019 Q1 answer: the original-language `<title>.md/.pdf` is still not written by this button. Alternative: always write a translated Markdown with no checkbox. If you choose that, drop acceptance 2 to 5 and use sub_doc=(".md",) whenever the target is not Original.
- Q2b. File names? Recommended: the same stem as the SRT, `<title>.<lang>.md` / `<title>.<lang>.pdf` (for example `Talk.de.md`, `Talk.sr-Latn.pdf`), in the transcribe folder. The original transcript keeps `<title>.md`, so nothing is overwritten.
- Q2c. What happens with target "Original" and the checkbox ticked? Recommended: write `<title>.<detected lang>.md/.pdf` in the spoken language, with no translation and no special case. Alternative: skip it with a log line.
- Q2d. What does the header say? Recommended: `- Language: <target code>` plus a new line `- Translated from: <source code>` (keyword `translated_from` in the exporter). The engine is not named. With translated_from=None the output is unchanged.
- Q2e. Is the SRT still written when only the document is wanted? Recommended: yes. Translate / Subtitles always writes the SRT, as today. A "document only" option is out of scope.

Design notes:
- The translated `Transcript` is `Transcript(segs, lang)`, where `segs` is the list already produced for the SRT and `lang = self._lang_code(target, t.language)`. Write the document(s) after translation and before `subtitles.write_srt`, at progress 0.85, so `saved[-1]` (the Open folder target from TASK-018) stays the SRT or video.
- Pass `translated_from=t.language` only when the target is not Original. Call it as a keyword so the existing 4-argument fakes in the `env` fixture of `tests/test_transcribe_screen.py` still work for the original path. New tests use fakes that accept the keyword.
- The `_run(url, out, model, md, pdf, local_file, language, subs, target, sub_video, engine, api_key, gemini_model, sub_doc=())` order matches `_args()` + `Screen._worker`, which passes `(url, out, *args)`. Check `app/screens/base.py` to confirm, but do not edit it.
- No change to `app/translator.py`, `app/subtitles.py`, `app/screens/base.py` or `app/ui.py`. Docs follow in TASK-025.

## Steps

1. Confirm that Q2a to Q2e have been answered and the acceptance criteria match the answers. Otherwise stop with `blocked`.
2. Add failing tests: the exporter `translated_from` header (`tests/test_core.py`), the `sub_doc` default, and `_args`/`_validate`/`_run` with the translated document (`tests/test_transcribe_screen.py`).
3. Add `translated_from` to `app/exporter.py` and `sub_doc` to `settings.DEFAULTS`.
4. Add the checkbox, `_args`, `_validate`, `collect_cfg` and the `_run` change in `app/screens/transcribe.py`.
5. Run every validation command and record the exit codes and pass counts in the handoff. The checkbox layout is not visually verified by tests; say so and list a manual check under `next_steps`.

## Blockers

Stop and write a handoff with `status: blocked` when the open questions are unanswered or the answers contradict the acceptance criteria, the change needs files outside `files_allowed`, or a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-022.md` (see templates/handoff.md)

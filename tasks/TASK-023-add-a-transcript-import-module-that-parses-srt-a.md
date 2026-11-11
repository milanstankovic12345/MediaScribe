---
id: TASK-023
title: Add a transcript import module that parses SRT and app Markdown into a Transcript
status: ready
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: []
files_allowed: ["app/transcript_import.py", "tests/test_transcript_import.py"]
files_excluded: []
review: ["code", "security"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcript_import.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "New UI-free module app/transcript_import.py (imports only the stdlib, app.transcriber and app.translator; both are light at import time) with TRANSCRIPT_EXTS = {\".srt\", \".md\"}, parse_srt(text) -> list[Segment], parse_markdown(text) -> tuple[list[Segment], str | None, str | None] (segments, title, language) and load(path) -> tuple[Transcript, str] (transcript, title)"
  - "parse_srt accepts a UTF-8 BOM, CRLF or LF line endings, a missing or non-numeric index line, ',' or '.' before the milliseconds, and 1 or 2 hour digits; text lines of a cue are joined with one space; <i>/<b>/<font ...> style tags and {\\an8}-style braces are removed; cues with empty text or a malformed timing line are skipped; end < start is clamped to end = start; output order follows the file"
  - "parse_srt on the output of subtitles.to_srt(cues) returns segments equal to the cues with line breaks replaced by spaces and times within 1 ms (round-trip test)"
  - "parse_markdown reads the app's own format from exporter.to_markdown: title from the first '# ' line, language from '- Language: xx', segments from lines '**[MM:SS]** text' or '**[H:MM:SS]** text'; a non-blank, non-header line after a segment is appended to that segment's text with a space; segment end = min(next start, start + max(2.0, len(text) / 15)); the last segment ends at start + max(2.0, len(text) / 15) (round-trip test against exporter.to_markdown, starts exact to the second)"
  - "load(path) decodes utf-8-sig and falls back to cp1250 on UnicodeDecodeError; title = Markdown '# ' title if present, else the file stem with a trailing language suffix removed when that suffix is a known code ('Talk.de.srt' -> 'Talk', 'Talk.sr-Latn.srt' -> 'Talk', 'My.Talk.srt' -> 'My.Talk'); Transcript.language = Markdown header language, else the known filename suffix ('sr-Latn' maps to 'sr', 'und' maps to ''), else ''"
  - "load raises ValueError with a message naming the file (name only) when the extension is not in TRANSCRIPT_EXTS or no segment was found; a file larger than 20 MB is rejected with ValueError before reading"
  - "Tests cover each rule above with in-memory strings and tmp_path files; nothing touches the network, Whisper, NLLB or ffmpeg; no new dependency; the full suite passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-11
---

## Objective

Add a pure parser module that turns an existing `.srt` file, or a Markdown transcript written by this app, into a `Transcript` of timed `Segment`s plus a title, so that Translate / Subtitles can start without Whisper (wired in TASK-024).

## Context

Source of the request: Q3 in `tasks/TASK-019-split-the-transcribe-screen-action-into-separate.md` (answered "follow-up task").

OPEN QUESTIONS (task stays `draft` until a human answers; the acceptance criteria assume the recommended answers):

- Q3a. Which import formats are accepted? Recommended: `.srt` and Markdown written by this app (`exporter.to_markdown`, including the translated documents from TASK-022). PDF import is not supported because it would need a PDF-parsing dependency. Plain `.txt` has no timestamps. WebVTT (`.vtt`) would be easy to add later but is not in this task.
- Q3b. How do SRT and Markdown timings map to segments? Recommended: SRT is 1:1, one cue becomes one Segment with its exact times, and cues are not merged into sentences. Markdown has only start times to the second, so end = min(next start, start + max(2 s, chars / 15)). This reading-speed cap keeps `subtitles.to_cues` from splitting a short line across a long silent gap.
- Q3c. Where does the source language come from? Recommended: the Markdown `- Language:` header, else the `<title>.<lang>.srt` filename suffix the app writes, else unknown (''). The screen's Language menu overrides this when it is not Auto (TASK-024).
- Q3d. What is the output title? Recommended: the Markdown `# ` title, else the file stem without a known language suffix, so that `Talk.en.srt` translated to German gives `Talk.de.srt`.
- Q3e. Which text encoding? Recommended: UTF-8 (with or without BOM), with a cp1250 fallback for older Serbian/Croatian SRTs.

Design notes:
- "Known language code" means a value of `transcriber.LANGUAGES` (excluding None), a key of `translator.WHISPER_TO_NLLB`, `sr-Latn` or `und`. Import `app.translator` only for its constant dicts. It loads CTranslate2 lazily, so importing it is cheap.
- `Segment` and `Transcript` live in `app/transcriber.py`. Reuse them and do not add new dataclasses.
- Keep the regexes linear (no nested quantifiers). The security review checks this module because it parses user-chosen files.
- This module is not wired into the UI here. TASK-024 does that, and TASK-025 documents it. It can run in parallel with TASK-021 and TASK-022 because the file scopes are disjoint.

## Steps

1. Confirm that Q3a to Q3e have been answered and the acceptance criteria match the answers. Otherwise stop with `blocked`.
2. Write `tests/test_transcript_import.py` with failing tests for every acceptance rule, including the round trips through `subtitles.to_srt` and `exporter.to_markdown`.
3. Implement `app/transcript_import.py`.
4. Run every validation command and record the exit codes and pass counts in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when the open questions are unanswered or the answers contradict the acceptance criteria, the change needs files outside `files_allowed`, or a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-023.md` (see templates/handoff.md)

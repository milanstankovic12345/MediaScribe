---
id: TASK-002
title: "Add subtitles module: SRT timing, cue splitting and SRT writer"
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: []
files_allowed: ["app/subtitles.py", "tests/test_subtitles.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_subtitles.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - fmt_srt_time(3725.5) returns 01:02:05,500
  - to_cues splits a 20 s / 200-char Segment into cues each <= 6 s and <= 84 chars, times monotonic and non-overlapping, covering the original start..end
  - each cue text is wrapped to at most 2 lines
  - write_srt writes UTF-8 with BOM, numbered blocks, 'start --> end' lines and keeps non-ASCII text (čšžđć) intact
  - module has no UI or ffmpeg imports
max_retries: 2
attempts: 1
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Create `app/subtitles.py` with pure functions that turn timed `Segment`s into readable subtitle cues and an SRT file.

## Context

Feature plan: `C:\Users\milla\.claude\plans\analyze-this-project-and-purrfect-flute.md`.
- Input type: `Segment(start, end, text)` from `app/transcriber.py`. Whisper segments can be up to ~30 s long, so they must be split into cues.
- Functions: `fmt_srt_time(seconds) -> "HH:MM:SS,mmm"`, `to_cues(segments, max_chars=84, max_dur=6.0) -> list[Segment]`, `to_srt(cues) -> str`, `write_srt(cues, path) -> Path`.
- Splitting: prefer sentence end, then comma, then word boundary; distribute the segment duration proportionally to character count; wrap each cue to <= 2 lines of ~42 chars (use `\n` inside the cue text).
- `write_srt` uses `encoding="utf-8-sig"` (BOM) so Windows players show Serbian/Croatian letters; create parent dirs like `exporter.write_markdown`.
- Put tests in the new file `tests/test_subtitles.py` (kept separate from `tests/test_core.py` so tasks can run in parallel).
- Rules (CLAUDE.md): core modules are UI-free and take plain callbacks (`cb: Callable[[float], None]`, `log: Callable[[str], None]`); no new dependencies without a reason in docs/techstack.md; tests never hit the network or run real Whisper/ffmpeg/models.
- TASK-004 will later add ffmpeg functions to this same module; do not add them here.

## Steps

1. Write failing tests in `tests/test_subtitles.py` for every acceptance criterion (incl. empty text segment and a segment shorter than max_dur that must stay one cue).
2. Implement `fmt_srt_time`, `to_cues`, `to_srt`, `write_srt`.
3. Run every validation command and record exit codes in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when: the change needs files
outside `files_allowed`, an acceptance criterion is ambiguous, a dependency
is missing, or a validation command cannot run in this environment. Never
widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-002.md` (see templates/handoff.md)

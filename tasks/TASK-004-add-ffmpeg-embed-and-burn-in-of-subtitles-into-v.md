---
id: TASK-004
title: Add ffmpeg embed and burn-in of subtitles into video
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-002"]
files_allowed: ["app/subtitles.py", "tests/test_subtitles.py"]
files_excluded: []
review: ["code", "security"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_subtitles.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - embed() builds an ffmpeg command with -c copy and -c:s mov_text for .mp4 (srt for .mkv) plus a language metadata tag
  - burn() runs ffmpeg with cwd set to the temp dir and a bare SRT filename in the subtitles filter (no Windows drive-letter escaping)
  - burn() reports progress from -progress out_time against duration
  - both use CREATE_NO_WINDOW on Windows and raise a readable error containing ffmpeg's stderr tail on failure
  - tests monkeypatch subprocess and never run real ffmpeg
max_retries: 2
attempts: 0
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Add `embed()` (soft subtitle track, no re-encode) and `burn()` (hard-coded subtitles, re-encode) to `app/subtitles.py` using ffmpeg.

## Context

Feature plan: `C:\Users\milla\.claude\plans\analyze-this-project-and-purrfect-flute.md`.
- Follow `app/audio_prep.py` for subprocess style: list args, `capture_output`, `creationflags=subprocess.CREATE_NO_WINDOW` on win32.
- `embed(video, srt, dst, lang_iso, log=None) -> Path`: `ffmpeg -y -i video -i srt -map 0 -map 1 -c copy -c:s mov_text -metadata:s:s:0 language=<iso639-2> dst` (`-c:s srt` when dst is .mkv). Map 2-letter Whisper codes to ISO 639-2 (en->eng, sr->srp, hr->hrv, bs->bos, de->deu, ...).
- `burn(video, srt, dst, duration=None, cb=None, log=None) -> Path`: copy the SRT next to a temp working dir and run ffmpeg with `cwd=<that dir>` and `-vf subtitles=<bare filename>` to avoid the Windows `C\:` escaping problem in the filter graph; `-c:v libx264 -crf 20 -preset veryfast -c:a copy -progress pipe:1`. Use `subprocess.Popen`, parse `out_time_ms=` lines and call `cb(min(t/duration, 1))` when duration is known.
- On a non-zero exit raise `RuntimeError` with the last ~5 lines of ffmpeg stderr.
- Rules (CLAUDE.md): core modules are UI-free and take plain callbacks (`cb: Callable[[float], None]`, `log: Callable[[str], None]`); no new dependencies without a reason in docs/techstack.md; tests never hit the network or run real Whisper/ffmpeg/models.

## Steps

1. Add failing tests to `tests/test_subtitles.py` that monkeypatch `subprocess.run` / `subprocess.Popen` and assert the exact command, cwd and flags, plus progress parsing and the error message.
2. Implement `embed` and `burn`.
3. Run every validation command and record exit codes in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when: the change needs files
outside `files_allowed`, an acceptance criterion is ambiguous, a dependency
is missing, or a validation command cannot run in this environment. Never
widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-004.md` (see templates/handoff.md)

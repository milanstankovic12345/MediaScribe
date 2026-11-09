---
id: TASK-005
title: Add opt-in ffmpeg smoke test for subtitle embed and burn
status: done
agent: test-engineer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-004", "TASK-009"]
files_allowed: ["tests/test_e2e_subtitles.py", "pytest.ini"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_e2e_subtitles.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - test is skipped unless env YT_TOOL_E2E=1 and ffmpeg/ffprobe are on PATH, so the default suite stays offline
  - with YT_TOOL_E2E=1 it generates a 3 s lavfi test video, writes a 2-cue SRT with non-ASCII text, runs embed() and asserts ffprobe reports a subtitle stream, runs burn() and asserts a playable output with no subtitle stream
  - all files live under tmp_path
max_retries: 2
attempts: 0
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Add an opt-in end-to-end test that runs the real ffmpeg on a generated clip to prove `embed()` and `burn()` produce valid videos.

## Context

Feature plan: `C:\Users\milla\.claude\plans\analyze-this-project-and-purrfect-flute.md`.
- The default suite must stay offline and fast: skip unless `os.environ.get("YT_TOOL_E2E") == "1"` and `shutil.which("ffmpeg")` and `shutil.which("ffprobe")`.
- Generate input with `ffmpeg -f lavfi -i testsrc=duration=3:size=320x240:rate=25 -f lavfi -i sine=duration=3 -shortest -c:v libx264 -c:a aac in.mp4`.
- Build cues with `subtitles.to_cues` / `write_srt` (non-ASCII text, e.g. "Zdravo, čšžđć").
- Check streams with `ffprobe -v error -show_entries stream=codec_type -of csv=p=0`.
- Only create `pytest.ini` if a marker registration is needed; otherwise leave it out.
- Do not edit production code; report defects in the handoff.

## Steps

1. Write `tests/test_e2e_subtitles.py` with the skip guard and two tests (embed, burn).
2. Run the default validation (tests skipped) and, if ffmpeg is available, also `YT_TOOL_E2E=1 .venv/Scripts/python -m pytest tests/test_e2e_subtitles.py -q`; record both results.
3. Record exit codes in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when: the change needs files
outside `files_allowed`, an acceptance criterion is ambiguous, a dependency
is missing, or a validation command cannot run in this environment. Never
widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-005.md` (see templates/handoff.md)

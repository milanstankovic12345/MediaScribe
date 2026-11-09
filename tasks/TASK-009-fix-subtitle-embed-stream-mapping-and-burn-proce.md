---
id: TASK-009
title: Fix subtitle embed stream mapping and burn process cleanup
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-004"]
files_allowed: ["app/subtitles.py", "tests/test_subtitles.py"]
files_excluded: []
review: ["code", "security"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_subtitles.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - embed() maps exactly -map 0:v -map 0:a? -map 1:0 in that order (no bare -map 0), so the new subtitle is output stream s:0 and -metadata:s:s:0 language=<iso639-2> tags it; a test asserts the full command list with ==
  - if cb, log or the stdout loop raises inside burn(), the ffmpeg process is killed and waited before the original exception propagates; a test with a fake Popen and a raising cb asserts kill() and wait() were called and the original exception type is re-raised
  - embed and burn tests compare the complete ffmpeg cmd list with == and assert creationflags == subtitles._flags()
  - new tests cover burn with duration=None (no progress calls before the final cb(1.0)), an out_time_ms=N/A line (ignored, no crash), and Popen/run raising OSError (RuntimeError mentioning ffmpeg could not be started) for both embed and burn
  - tests still monkeypatch subprocess and never run real ffmpeg; full suite passes
max_retries: 2
attempts: 0
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Fix review findings CR-1, CR-2 and CR-3 (SEC-1 duplicates CR-2) from TASK-004 so `embed()` tags the right subtitle stream and `burn()` never leaks an ffmpeg process.

## Context

- Findings: `reports/reviews/TASK-004-code.md` (CR-1, CR-2, CR-3) and `reports/reviews/TASK-004-security.md` (SEC-1 = CR-2). Source task: `tasks/TASK-004-add-ffmpeg-embed-and-burn-in-of-subtitles-into-v.md`.
- CR-1 (`app/subtitles.py` `embed`): `-map 0 -map 1` makes an existing source subtitle track output `s:0`, so `-metadata:s:s:0` tags the old track and leaves the new one untagged; `-map 0` also copies attachments/data/PGS streams that mp4/mov_text reject. Decision: use `-map 0:v -map 0:a? -map 1:0`. Existing source subtitle tracks are intentionally dropped (do not add `-map 0:s?`; it would bring back bitmap subs that mp4 rejects). Keep `-c copy -c:s mov_text|srt` and the metadata tag unchanged.
- CR-2 (`burn`): wrap the stdout loop and `proc.wait()` so any exception (`BaseException`) kills and waits the process, then re-raises the original exception. This must happen inside the `TemporaryDirectory` block so ffmpeg has exited before the temp dir is removed (Windows cannot delete the child's cwd).
- CR-3 (`tests/test_subtitles.py`): compare complete `cmd` lists with `==`, assert `kwargs["creationflags"] == sb._flags()`, add tests for `duration=None`, `out_time_ms=N/A`, and OSError on start for embed (`subprocess.run`) and burn (`subprocess.Popen`).
- Out of scope (do not do here): CR-4 test import cleanup, CR-5 iso639_2 coverage, CR-6 audio fallback, SEC-2 `-f srt`/protocol whitelist, SEC-3 `.resolve()` in embed.
- Rules (CLAUDE.md): core modules stay UI-free with plain callbacks; no new dependencies; tests never run real ffmpeg or hit the network.

## Steps

1. Update the embed tests to assert the full command with `-map 0:v -map 0:a? -map 1:0` for .mp4 and .mkv, plus exact `creationflags`; tighten the burn command assertion the same way. Confirm they fail.
2. Add tests: burn with a raising `cb` and a fake Popen recording `kill`/`wait` (original exception propagates); burn with `duration=None`; burn with an `out_time_ms=N/A` line; embed and burn with OSError on start -> `RuntimeError`.
3. Change the map arguments in `embed()` and add the kill/wait guard in `burn()`.
4. Run every validation command and record exit codes in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when: the change needs files
outside `files_allowed`, an acceptance criterion is ambiguous, a dependency
is missing, or a validation command cannot run in this environment. Never
widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-009.md` (see templates/handoff.md)

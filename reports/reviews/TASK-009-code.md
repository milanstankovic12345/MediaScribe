---
task: TASK-009
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/subtitles.py (full file; embed and burn in detail)
  - tests/test_subtitles.py (full file)
  - tasks/TASK-009-fix-subtitle-embed-stream-mapping-and-burn-proce.md
  - reports/handoffs/TASK-009.md
  - reports/reviews/TASK-004-code.md
  - reports/reviews/TASK-004-security.md
not_checked:
  - Real ffmpeg run of the new embed map against a source that already has subtitle tracks (read-only guard blocks writing media files)
  - Real Popen kill/wait on Windows with a live ffmpeg child and TemporaryDirectory cleanup
  - Callers / UI wiring of embed and burn (other tasks)
findings:
  - id: CR-1
    severity: low
    title: No test guards that the kill/wait happens before TemporaryDirectory cleanup
    location: tests/test_subtitles.py:219-233
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: info
    title: kill() and wait() share one try block, so a raising kill() skips wait()
    location: app/subtitles.py:192-198
    confidence: 70
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: embed now drops existing source subtitle tracks and requires a video stream (documented decision)
    location: app/subtitles.py:143-145
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
---

## Validation re-run (by reviewer)

- `.venv/Scripts/python -m pytest tests/test_subtitles.py -q` -> exit 0, 24 passed (matches handoff)
- `.venv/Scripts/python -m pytest -q` -> exit 0, 51 passed (matches handoff)
- In-memory mutation checks (source patched in `sys.modules`, no files written):
  - removed `proc.kill()` from the except branch -> `test_burn_cb_raises_kills_and_waits` fails (exit 1)
  - reverted maps to `-map 0 -map 1` -> `test_embed_mp4_command` and `test_embed_mkv_uses_srt` fail (exit 1)
  So the new tests do pin the CR-1 and CR-2 fixes from TASK-004.

## Acceptance criteria

1. embed maps `-map 0:v -map 0:a? -map 1:0` in that order with no bare `-map 0` (app/subtitles.py:143-145); the tests compare the full list with `==` for .mp4 and .mkv (tests:112-142). Met.
2. burn wraps the stdout loop and `proc.wait()` in `try/except BaseException`, kills and waits, then uses a bare `raise`, all inside the `TemporaryDirectory` block (app/subtitles.py:179-198). `test_burn_cb_raises_kills_and_waits` uses a raising cb (KeyError) and asserts `killed == 1`, `waited >= 1`, and that the KeyError propagates. Met.
3. Full `cmd ==` plus `creationflags == sb._flags()` for embed (both tests) and burn (tests:200-204). Met.
4. duration=None -> `got == [1.0]`; `out_time_ms=N/A` -> `[0.5, 1.0]`, no crash; OSError -> RuntimeError "ffmpeg could not be started" for both embed (`subprocess.run`) and burn (`subprocess.Popen`). Met.
5. subprocess is monkeypatched everywhere; full suite passes. Met.

TASK-004 CR-1, CR-2 (= SEC-1, except the optional timeout) and CR-3 are resolved. Out-of-scope items (CR-4/5/6, SEC-2/3) are unchanged, as the task requires.

## Findings

### CR-1 - No test guards that kill/wait happens before temp-dir cleanup (Low, confidence 85)

- **Location:** `tests/test_subtitles.py:219-233` (code under test: `app/subtitles.py:166-198`)
- **Impact:** The task context says the guard must sit inside the `TemporaryDirectory` block so ffmpeg has exited before Windows tries to delete its cwd. The code does that today, but no test pins it. If someone later moves the try/except outside the `with` (for example, wrapping the whole block), every test stays green. On Windows, cleanup would then run while ffmpeg is alive, raise `PermissionError`, and hide the original exception. That is the exact failure TASK-004 CR-2 described.
- **Reproduction:** Move the `try/except BaseException` around the whole `with tempfile.TemporaryDirectory()` block. The fake `_Proc` holds no OS handle on the dir, so cleanup succeeds and `test_burn_cb_raises_kills_and_waits` still passes. Reasoned from the code; not executed, because of the read-only guard.
- **Recommended fix:** In the fake Popen, record `kw["cwd"]`. In `_Proc.kill`, assert `Path(cwd).exists()` (or record it), then assert in the test that the temp dir still existed when kill ran.

### CR-2 - kill() and wait() share one try (Info, confidence 70)

- **Location:** `app/subtitles.py:192-198`
- **Impact:** If `proc.kill()` raises, `proc.wait()` is skipped and the process is not reaped. In CPython this is unlikely: `Popen.kill` handles an already-exited child on Windows (PermissionError -> exit-code check) and on POSIX. So this is robustness only.
- **Recommended fix (optional):** Put `kill()` in its own `try/except OSError`, then call `wait()`.

### CR-3 - embed behaviour change (Info, confidence 90)

- **Location:** `app/subtitles.py:143-145`
- **Note:** Existing subtitle tracks, attachments and data streams in the source are now dropped. This was the stated decision (no `-map 0:s?`). `-map 0:v` is not optional, so an audio-only input makes ffmpeg fail with "matches no streams". That is fine for a video-embed function, and the error surfaces through the stderr tail. When this is wired into the UI, the UI or docs should mention that old subtitle tracks are replaced.

## Questions

- SEC-1 also mentioned the lack of a timeout on a stalled ffmpeg. The task scoped that out implicitly, since only the kill/wait guard was required. Left for the orchestrator to decide.

## Coverage statement

Read all of `app/subtitles.py` and `tests/test_subtitles.py`, the task file, the handoff, and the TASK-004 code and security reviews. Ran both validation commands and two in-memory mutation checks. Checked CPython `Popen.kill` semantics by reasoning, not by execution. Not checked: a real ffmpeg embed on a source with existing subtitle tracks, a real Windows kill and temp-dir cleanup with a live child, and callers/UI wiring. git diff shows nothing because the files are untracked, so the whole files were judged against the TASK-004 findings. Scope compliance was not verified against git; the README.md and requirements.txt modifications in the working tree predate this task per the session git snapshot and are not attributed to it. No findings does not prove correctness.

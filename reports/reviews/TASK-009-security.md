---
task: TASK-009
kind: security
reviewer: security-reviewer
model: claude-opus-5-5
round: 1
verdict: approve
scope_checked:
  - app/subtitles.py (full file; embed() and burn() traced line by line)
  - tests/test_subtitles.py (full file; embed/burn tests at lines 100-264)
  - reports/reviews/TASK-004-security.md (SEC-1..SEC-3) and the TASK-009 task/handoff claims
  - callers of embed()/burn() under app/ (grep found none)
not_checked:
  - Real ffmpeg/libass runtime behaviour (tests mock subprocess; not executed)
  - Live check of kill()/wait() on a real child process (a scratch script was blocked by the read-only guard; behaviour judged from code and CPython Popen semantics)
  - UI wiring of embed()/burn() (does not exist yet)
  - app/translator.py and other untracked files outside this task
findings:
  - id: SEC-1
    severity: info
    title: burn() still has no stall timeout; error-path wait() after kill() is unbounded
    location: app/subtitles.py:179-198
    confidence: 55
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-2
    severity: info
    title: proc.stdout pipe is not explicitly closed on the error path
    location: app/subtitles.py:171-198
    confidence: 60
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### Verification of the TASK-004 finding this task targets

TASK-004 SEC-1 (= CR-2, orphaned ffmpeg when the callback raises) is **fixed, verified by reading the code and running the tests**:
- `app/subtitles.py:179-198`: the stdout loop and `proc.wait()` are inside `try ... except BaseException:`. The handler calls `proc.kill()` and then `proc.wait()`, swallows only `Exception` from those calls, and re-raises the original exception with a bare `raise`. `KeyboardInterrupt`/`SystemExit` are covered too.
- The guard sits inside the `with tempfile.TemporaryDirectory()` block, so the child has been killed and reaped before `TemporaryDirectory.__exit__` removes its cwd. That removes the Windows `PermissionError` that could have masked the original exception.
- The `Popen` `OSError` path raises before `proc` exists, so the handler never sees an unbound `proc`.
- `test_burn_cb_raises_kills_and_waits` (line 219) uses a fake Popen and a raising `cb`. It asserts `KeyError` propagates, `killed == 1` and `waited >= 1`. It does not assert that `kill` comes before `wait`, but the code order is correct.

`embed()` mapping change (`-map 0:v -map 0:a? -map 1:0`, line 143-145): from a security view this narrows what is copied from untrusted downloaded media. Attachment, data and source subtitle streams are no longer passed through to the output. The subtitle stream is now `s:0`, so the `language=` tag lands on the stream we produced. Arguments are still a list with no `shell=True`. The metadata value is still limited to `iso639_2()` output (3 letters or `und`). No new injection surface.

Tests confirm full command equality and `creationflags == sb._flags()` (CREATE_NO_WINDOW on win32) for embed (.mp4/.mkv) and burn. They also cover the OSError-to-RuntimeError path for both, and `duration=None` and `out_time_ms=N/A`. I ran them: 24 passed in tests/test_subtitles.py and 51 passed in the full suite, matching the handoff.

### SEC-1 - No stall timeout; unbounded wait() after kill() (Info, confidence 55)

- **Category:** CWE-400 Uncontrolled Resource Consumption
- **Location:** `app/subtitles.py:179-198`
- **Scenario:** A crafted or truncated downloaded video makes ffmpeg stall without closing stdout. `for line in proc.stdout` then blocks forever and the worker thread hangs, because no timeout or cancel path exists. Separately, if `kill()` fails (for example access denied), the follow-up `proc.wait()` has no timeout and can block the worker inside the exception handler.
- **Impact:** Local only. A stuck worker thread and a lingering ffmpeg process. No confidentiality or integrity impact. This is the leftover "no timeout" half of TASK-004 SEC-1, which this task did not cover.
- **Fix:** Use `proc.wait(timeout=5)` in the handler, wrapped like the current `except Exception`. Add a cancel or watchdog mechanism when the UI wires burn() in.
- **Test:** A fake Popen whose `wait(timeout=...)` records the timeout argument. Assert that a timeout is passed on the error path.

### SEC-2 - stdout pipe not explicitly closed on the error path (Info, confidence 60)

- **Category:** CWE-404 Improper Resource Shutdown
- **Location:** `app/subtitles.py:171-198`
- **Scenario:** `Popen` is not used as a context manager, and `proc.stdout` is never closed. After kill/wait the pipe handle stays open until garbage collection. In a playlist loop with repeated failures, this leaks handles one per item for a short time.
- **Impact:** Negligible. A short-lived handle leak.
- **Fix:** Use `with subprocess.Popen(...) as proc:` (it closes the pipes and waits on exit) inside the existing guard, or call `proc.stdout.close()` in a `finally`.
- **Test:** Give the fake Popen a stdout object with a `close()` that records the call, and assert it was called on both the success and error paths.

### Carried-over items (not changed by this task, still open from TASK-004)

- TASK-004 SEC-2 (Info): no `-f srt` / `-protocol_whitelist file` on ffmpeg inputs. This was out of scope for TASK-009 and is unchanged.
- TASK-004 SEC-3 (Info): `embed()` still passes unresolved `video`/`srt`/`dst`, so a relative `dst` beginning with `-` would be parsed as an ffmpeg option. This was out of scope and is unchanged. Re-check when embed() gets a caller.

## Coverage statement

Entry points reviewed: `embed()` and `burn()` parameters (paths, `lang_iso`, `duration`, `cb`, `log`), traced to the subprocess sink (argument list, creationflags), the ffmpeg option and filtergraph parsers, the temp-dir filesystem sink, the exception and cleanup paths, and the error text. References applied: OWASP Top 10 baseline and input validation (command, argument and filter injection), plus resource shutdown. Tools run: pytest on tests/test_subtitles.py (24 passed) and the full suite (51 passed). Not run: real ffmpeg, a live child-process kill check (blocked by the read-only guard), or fuzzing. Not reviewed: UI callers (none exist), translator.py. This review does not show the module is secure. It records only what was checked.

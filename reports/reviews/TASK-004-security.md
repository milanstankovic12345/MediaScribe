---
task: TASK-004
kind: security
reviewer: security-reviewer
model: claude-opus-5-5
round: 1
verdict: approve
scope_checked:
  - app/subtitles.py (embed, burn, iso639_2, _flags, _tail; full file read)
  - tests/test_subtitles.py (embed/burn tests)
  - app/audio_prep.py (reference subprocess pattern)
  - app/downloader.py safe_name and _BAD_CHARS (origin of path components)
not_checked:
  - Callers of embed()/burn() (none exist yet; UI wiring is a later task) - path origin and dst selection must be re-checked when wired
  - Real ffmpeg/libass behaviour (not executed; tests mock subprocess)
  - app/translator.py and other untracked files outside this task
findings:
  - id: SEC-1
    severity: low
    title: burn() leaves ffmpeg running if the progress callback or stdout loop raises; no timeout
    location: app/subtitles.py:171-190
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-2
    severity: info
    title: ffmpeg inputs are content-probed with no format or protocol restriction
    location: app/subtitles.py:143,168
    confidence: 40
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-3
    severity: info
    title: embed() passes unresolved paths; a relative output path starting with '-' is parsed as an ffmpeg option
    location: app/subtitles.py:141-145
    confidence: 60
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

Verified controls (read in code, not taken from the handoff):
- Both functions build ffmpeg commands as argument lists with no `shell=True`. That rules out shell injection (CWE-78).
- The burn-in filter graph is the fixed literal `subtitles=subs.srt`. The SRT is copied into a fresh `tempfile.TemporaryDirectory()` (mkdtemp, per-user location) under a fixed name, and that directory is the child cwd. No caller-controlled text reaches the filtergraph parser, so filtergraph injection and Windows `C\:` escaping are not possible.
- `iso639_2()` returns a 3-letter alphabetic code or `und`, so the `-metadata` value cannot carry option or `:`/`=` payloads.
- `video` and `srt` always follow `-i` and are consumed as option values, so a leading `-` cannot turn them into options.
- `CREATE_NO_WINDOW` is used on win32. Error text contains only the ffmpeg stderr tail, and it goes to the local UI log. There is no cross-boundary leak.
- 19/19 tests in tests/test_subtitles.py pass (run in this session).

### SEC-1: Orphaned ffmpeg process on callback exception, and no timeout (Low, confidence 80)

- **Category:** CWE-404 Improper Resource Shutdown / CWE-400 Uncontrolled Resource Consumption
- **Location:** `app/subtitles.py:171-190`
- **Scenario:** `cb` comes from the UI layer. If it raises, for example during a cancel or after a queue or widget error, the exception leaves the `for line in proc.stdout` loop without `proc.kill()`/`proc.wait()`. The libx264 re-encode keeps running in the background with a full CPU load and keeps writing `dst`. Meanwhile `TemporaryDirectory.__exit__` tries to remove the working dir that ffmpeg is using as cwd. On Windows that can raise `PermissionError` and hide the original exception. If ffmpeg stalls on a malformed input, the loop blocks forever because there is no timeout.
- **Impact:** Local only. Background resource exhaustion, a partial output file, and a stuck worker thread. Not attacker-controlled beyond feeding crafted media.
- **Fix:** Wrap the loop in `try: ... except BaseException: proc.kill(); proc.wait(); raise` (or `finally` with `if proc.poll() is None: proc.kill()`). Optionally pass `ignore_cleanup_errors=True` to `TemporaryDirectory`.
- **Test:** A fake Popen whose `kill` records a call, plus a `cb` that raises. Assert that `kill` was called and the original exception propagates.

### SEC-2: Unrestricted input probing by ffmpeg (Info, confidence 40)

- **Category:** CWE-20 / OWASP A05. This is the known class where ffmpeg demuxer probing reads local files, for example an HLS playlist hidden in a media container.
- **Location:** `app/subtitles.py:143` (`-i str(srt)` with no `-f srt`), `app/subtitles.py:168` (`-i str(video)`)
- **Scenario:** The downloaded video is untrusted content from an uploader. ffmpeg picks the demuxer from content, not from the file extension. A crafted file that probes as a playlist could make ffmpeg open other local paths. In `burn()`, their content could then be rendered into the re-encoded frames, which the user might later share. Current ffmpeg builds restrict HLS segment extensions and protocols, and the SRT written by `write_srt` starts with a fixed BOM and `1\n00:...` header, so I could not show this to be exploitable here. The same exposure already exists in `audio_prep.prepare`, so it is not new to this task.
- **Fix (hardening):** Add `-f srt` before the SRT `-i` in `embed()`. Consider adding `-protocol_whitelist file` before each `-i` so inputs can only be local files.
- **Test:** Assert that the command contains `-f`, `srt` immediately before the SRT `-i`, and that `-protocol_whitelist` precedes each `-i`.

### SEC-3: embed() uses unresolved paths, so the positional output can be read as an option (Info, confidence 60)

- **Category:** CWE-88 Argument Injection
- **Location:** `app/subtitles.py:141-145`
- **Scenario:** `dst` is the last positional argument and has no `-i`-style guard. `downloader.safe_name` keeps a leading `-`, because `_BAD_CHARS` does not strip it. If a future caller passes a relative `dst` built from a video title such as `-y.mp4` or `-f.mp4`, ffmpeg parses it as an option. Today this only produces an ffmpeg error or a wrong output location, not code execution. `burn()` already calls `.resolve()` on its paths, which closes this gap there.
- **Fix:** Call `.resolve()` on `video`, `srt` and `dst` in `embed()`, as `burn()` does, so every path is absolute and starts with a drive letter.
- **Test:** `embed(Path("v.mp4"), Path("s.srt"), Path("-x.mp4"), "en")`, then assert that the last command element is absolute.

## Coverage statement

Entry points reviewed: `embed()` and `burn()` parameters (video, srt and dst paths, `lang_iso`, `duration`, `cb`, `log`), traced to the subprocess sink, the ffmpeg option and filtergraph parsers, the temp-dir filesystem sink, and the error and log output. References applied: OWASP Top 10 baseline and input validation (command, argument and filter injection). Tools run: pytest on tests/test_subtitles.py (19 passed). Not run: real ffmpeg, libass, or any fuzzing of media inputs. Not reviewed: callers (none exist yet), translator.py, the UI layer. When `embed()`/`burn()` are wired into the UI, re-check where `dst` comes from and whether it can equal `video`. This review does not show the module is secure. It records only what was checked.

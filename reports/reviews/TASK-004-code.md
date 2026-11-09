---
task: TASK-004
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/subtitles.py
  - tests/test_subtitles.py
  - app/audio_prep.py
  - app/downloader.py
  - reports/handoffs/TASK-004.md
not_checked:
  - File-based embed/burn run on real media (read-only guard blocks writes; TASK-005 covers it)
  - libass font rendering; UI wiring (TASK-006)
findings:
  - id: CR-1
    severity: medium
    title: embed uses -map 0 plus -metadata:s:s:0, so an existing source subtitle track gets the language tag and the new track is untagged; attachments/bitmap subs break mp4 output
    location: app/subtitles.py:143-145
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: burn does not kill/wait ffmpeg if the read loop or cb raises
    location: app/subtitles.py:171-190
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: Tests do not assert the exact command or flag values; several branches untested
    location: tests/test_subtitles.py:112-193
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: Mid-file and duplicate imports in the test module
    location: tests/test_subtitles.py:100-104
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-5
    severity: info
    title: iso639_2 misses many Whisper languages (fall back to und)
    location: app/subtitles.py:112-127
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-6
    severity: info
    title: burn always copies audio; mp4-incompatible source audio fails
    location: app/subtitles.py:170
    confidence: 70
    status: open
    verified: false
    acceptance_ref: null
---

## Validation re-run (by reviewer)

- `.venv/Scripts/python -m pytest tests/test_subtitles.py -q` -> exit 0, 19 passed (matches handoff)
- `.venv/Scripts/python -m pytest -q` -> exit 0, 46 passed (matches handoff)
- Real ffmpeg 9.0.2, pipes only: `-progress pipe:1` prints `out_time_ms=2000000` for 2 s, so dividing by 1_000_000 is correct; a failing run ends with readable "Error opening input file ..." lines that the tail logic keeps.

All five acceptance criteria are met as written.

## Findings

### CR-1 - embed tags the wrong subtitle stream (Medium, confidence 95)

- **Location:** `app/subtitles.py:143-145`
- **Impact:** The plan allows local video input. With `-map 0`, a source that already has a subtitle track keeps it as output `s:0`, so `-metadata:s:s:0 language=X` relabels the old track and the new track has no language. `-map 0` also copies mkv attachments, data streams and bitmap subs (PGS), which mp4 / mov_text reject, so embed fails for such files. App-downloaded mp4s are unaffected.
- **Reproduction (executed):** video + subtitle tagged `fra`, then the embed args `-map 0 -map 1 -c copy -c:s srt -metadata:s:s:0 language=srp` -> ffprobe: index 1 subtitle `language=srp` (old track), index 2 subtitle with no tag (new track).
- **Recommended fix:** `-map 0:v -map 0:a? -map 1:0` (or append `-map 0:s?` after `1:0` to keep old text subs) so the new track is always `s:0`; add a test for the map order.

### CR-2 - burn not exception-safe (Low, confidence 80)

- **Location:** `app/subtitles.py:171-190`
- **Impact:** If cb/log raises during the stdout loop, `proc.wait()` is skipped: ffmpeg keeps encoding in the background, and on Windows TemporaryDirectory cleanup fails (child cwd is the temp dir), hiding the real error.
- **Reproduction:** `burn(..., cb=lambda p: 1/0)` on a real video. Reasoned from code, not executed.
- **Recommended fix:** `try: ... code = proc.wait()` / `except BaseException: proc.kill(); proc.wait(); raise`.

### CR-3 - Weak command assertions in tests (Low, confidence 95)

- **Location:** `tests/test_subtitles.py:112-193`
- **Impact:** Task step 1 asks to assert the exact command. Changing `-crf 20`, dropping `-map 1`, `-y` or `-c:a copy` keeps all tests green; `creationflags` is only checked for presence. Untested: `duration=None`, `out_time_ms=N/A`, OSError -> RuntimeError.
- **Recommended fix:** compare the full `cmd` lists with `==`, assert `kw["creationflags"] == sb._flags()`, add the three branch tests.

### CR-4 - Test imports (Info)

`import subprocess as _sp`, `Path as _P` and a second `pytest as _pytest` sit mid-file (E402 once a linter lands via TASK-001). Move them to the top.

### CR-5 - iso639_2 coverage (Info)

id, vi, th, fa, ca, lt, lv, et, ms and others map to `und`; consider mirroring `transcriber.LANGUAGES`.

### CR-6 - burn audio copy (Info)

`-c:a copy` into mp4 fails for e.g. Vorbis sources. The error is readable; optional fallback to aac.

## Coverage statement

Read all of `app/subtitles.py` (focus on iso639_2, _flags, _tail, embed, burn), the embed/burn tests, `app/audio_prep.py`, `app/downloader.py` and the feature plan. Ran both validation commands and pipe-only ffmpeg checks (progress units, error output, CR-1). Not checked: a file-based embed/burn run (guard blocks writes, even to the scratchpad), libass fonts on Windows, UI wiring. Security is a separate review. No findings does not prove correctness.

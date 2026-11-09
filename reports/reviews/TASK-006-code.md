---
task: TASK-006
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/screens/transcribe.py
  - app/settings.py
  - tests/test_core.py
  - app/screens/base.py
  - app/subtitles.py
  - app/translator.py
  - app/downloader.py
  - app/audio_prep.py
  - app/transcriber.py
not_checked:
  - UI not launched (no visual check)
  - real ffmpeg embed/burn (e2e tests skipped)
  - real yt-dlp, Whisper and NLLB
findings:
  - id: CR-1
    severity: medium
    title: Embed/Burn validation is skipped when a URL is also present, but _run uses the local file
    location: app/screens/transcribe.py:91
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: medium
    title: No tests for _validate, _lang_code, _run routing or invalid-setting fallback
    location: tests/test_core.py:152
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: MD/PDF files are written but never reported if the subtitle stage fails
    location: app/screens/transcribe.py:141
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: low
    title: MD/PDF-only runs park the progress bar at 0.6
    location: app/screens/transcribe.py:139
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-5
    severity: low
    title: Garbled 150-char condition line (lost line continuation)
    location: app/screens/transcribe.py:91
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-6
    severity: info
    title: tests/ is gitignored, so the new test is not in version control
    location: .gitignore:14
    confidence: 100
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-7
    severity: info
    title: Burn progress uses the last speech segment end as the video duration
    location: app/screens/transcribe.py:160
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - Embed/Burn validation skipped when a URL is also present (Medium, 95)
- Location: app/screens/transcribe.py:91 vs :125
- Acceptance: "Embed/Burn require a video file or URL"
- Impact: _validate rejects an audio-only local file only when url is empty, but _run always prefers local_file. URL plus a local .mp3 plus Embed/Burn passes validation, runs the full transcription, then ffmpeg fails (-map 0:v matches nothing).
- Reproduction (stubbed, this session): _validate with local_file=a.mp3, sub_video=EMBED, url=https://youtu.be/x returns None (same for BURN). _run with the same inputs called subtitles.embed with video=a.mp3; download_video was not called.
- Fix: drop the "not url" term so the check matches the precedence in _run.

### CR-2 - Missing tests for the screen logic (Medium, 90)
- Location: tests/test_core.py:152
- Impact: only the DEFAULTS values are tested. No tests for _validate, _lang_code (sr-Latn), download routing, output naming or progress. CR-1 would have been caught.
- Fix: Tk-free tests that call TranscribeScreen._validate / _lang_code / _run on a SimpleNamespace stub self with monkeypatched downloader, transcribe and subtitles. This review did exactly that.

### CR-3 - Saved MD/PDF not reported on later failure (Low, 90)
- Location: app/screens/transcribe.py:141-166
- Impact: MD/PDF are written before translation and embed/burn, but "Saved:" lines are logged only after the with block. Any later failure leaves files on disk that the log never mentions. Example: a ValueError for an unsupported source language (ja to English), a model download error, or an ffmpeg error.
- Fix: log each path when it is appended to saved.

### CR-4 - Progress bar parks at 0.6 for MD/PDF-only runs (Low, 95)
- Location: app/screens/transcribe.py:134,139
- Acceptance: "Markdown/PDF-only runs behave exactly as before"
- Impact: transcription used to map to 0.2-1.0 and now maps to 0.1-0.6 even with Subtitles off. The bar then jumps to 1.0 on Done. The Done text change was already disclosed.
- Fix: hi = 0.6 if subs else 1.0; map transcription to 0.1..hi.

### CR-5 - Garbled condition line (Low, 95)
- Location: app/screens/transcribe.py:91
- Impact: about 17 spaces in the middle of the if condition, which looks like a lost line continuation. Valid Python, but hard to read.
- Fix: wrap in parentheses over two lines when fixing CR-1.

### CR-6 - tests/ is gitignored (Info, 100)
- Location: .gitignore:14
- Impact: git check-ignore confirms tests/test_core.py is ignored, so git diff shows no test change. Pre-existing configuration; for the orchestrator to note.

### CR-7 - Burn progress uses the last segment end as the duration (Info, 85)
- Location: app/screens/transcribe.py:160
- Impact: with trailing non-speech the bar reaches 1.0 early. With no segments there is no burn progress. Cosmetic.
- Fix (optional): probe the media duration and keep the segment end as a fallback.

## Verified OK
- Thread safety: _run uses only its args, self._say, self._prog and the static _lang_code. Widgets are read in _args / collect_cfg on the main thread. _toggle_subs is a widget command.
- Queue protocol unchanged: _run returns a str; base _worker emits done/error.
- Settings defaults were added. Invalid sub_target / sub_video fall back in the screen, like model / language.
- _lang_code is correct for all 15 TARGETS (checked in this session).
- Progress split is 0.1/0.6/0.85/1.0. URL+Embed/Burn uses download_video in the temp dir, and embed/burn finish before cleanup. Names use safe_name.

## Questions (below threshold)
- Embed always writes .mp4 with stream copy. Local mkv/webm/avi with Vorbis or PCM audio would likely fail. Confidence 65.
- download_video uses the default Best quality; burning 4K is slow. Use cfg video_quality?
- Empty transcript plus Embed/Burn was not tried with real ffmpeg.

## Validation re-run (this session)
- .venv/Scripts/python -m pytest -q: exit 0, 52 passed, 2 skipped (e2e; YT_TOOL_E2E not set). Matches the handoff.
- .venv/Scripts/python -c "import app.screens.transcribe": exit 0.
- Stub probes (python on stdin, no files written): _validate 4 cases, _lang_code 15 targets, _run URL+local mp3+EMBED.

## Coverage statement
Inspected: the diff of transcribe.py and settings.py, the new test (read directly because tests/ is gitignored), and base.py, subtitles.py, translator.py, downloader.py, audio_prep.py and transcriber.py. Not checked: the UI was not launched (no visual check). Real ffmpeg, yt-dlp, Whisper and NLLB were not run. Finding no other defects does not prove correctness.

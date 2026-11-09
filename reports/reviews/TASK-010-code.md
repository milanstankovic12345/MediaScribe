---
task: TASK-010
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/screens/transcribe.py (git diff eab24b9, full _validate/_lang_code/_run read)
  - app/screens/base.py (_validate caller, url stripping)
  - app/translator.py (TARGETS, WHISPER_TO_NLLB, ORIGINAL, SERBIAN_LATIN)
  - tests/test_transcribe_screen.py (untracked, read directly)
  - reports/reviews/TASK-006-code.md (CR-1, CR-2, CR-5 originals)
  - tasks/TASK-010-fix-transcribe-embed-burn-validation-with-url-pl.md
  - reports/handoffs/TASK-010.md
not_checked:
  - Running the real GUI (no display check; logic is covered by Tk-free tests only)
  - Real ffmpeg / Whisper / NLLB behaviour (all monkeypatched by design)
  - CR-3, CR-4, CR-7 from TASK-006 (out of scope per task)
findings:
  - id: CR-1
    severity: low
    title: Unused src_dir setup in the _run test fixture
    location: tests/test_transcribe_screen.py:92
    confidence: 100
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: info
    title: Error text says "or a URL" even when the user already supplied a URL
    location: app/screens/transcribe.py:93
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: No _run test for local video file + Embed/Burn passing the local file as video_src
    location: tests/test_transcribe_screen.py:149
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
---

## Summary

The TASK-010 production change is limited to the `_validate` Embed/Burn condition in
`app/screens/transcribe.py` (lines 91-93): the `not url` term is gone and the condition is a
parenthesized two-line expression with no embedded run of spaces. This matches the `_run`
precedence (local_file always wins over URL), so TASK-006 CR-1 and CR-5 are resolved.
The new Tk-free test file covers every acceptance criterion. No blocking findings.

## Validation re-run (this session)

- `.venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q` -> exit 0, 46 passed
- `.venv/Scripts/python -m pytest -q` -> exit 0, 98 passed, 2 skipped
- `.venv/Scripts/python -c "import app.screens.transcribe"` -> exit 0

These match the handoff.

Mutation check (in-process, no file changes): replaced `TranscribeScreen._validate` with the
pre-fix condition (with `not url`) and ran the new test file -> exactly 2 failed
(`test_validate_rejects_audio_with_embed_burn[https://youtu.be/x-EMBED/BURN]`), 44 passed.
This confirms the handoff's red-step claim and that the tests actually lock in the CR-1 fix.

## Acceptance check

1. URL + local .mp3 and empty URL + local .mp3 with EMBED/BURN return the Embed/Burn message: covered (4 parametrized cases), passes.
2. None for local .mp4/.MKV with Embed/Burn, URL-only with Embed/Burn, local .mp3 SRT-only; rejects no URL/no file and no output: each has a test, passes.
3. Condition is parenthesized over two lines, no embedded spaces (checked with `cat -A`); behaviour otherwise unchanged (only `not url` removed relative to the TASK-006 condition described in TASK-006-code CR-1).
4. `_lang_code`: ORIGINAL with "de" and None ("und"), Serbian (Latin) -> "sr-Latn", every TARGETS label -> non-empty, no "_": covered.
5. `_run` routing: local file -> no downloader call and prepare gets the local path; URL+EMBED/BURN -> download_video; URL+SRT-only/MD-only/PDF-only -> download_audio_raw: covered.
6. Names `.en.srt`, `.en.mp4`, `.en.burned.mp4`, paths in the "Saved:" string, subtitle progress monotonic, contains 0.85, ends at 1.0 (3 modes x 2 targets): covered. MD/PDF-only final progress is not asserted, as instructed.
7. Tk-free: stub is a SimpleNamespace; no CTk widget or Tk root created; downloader, audio_prep, transcribe, exporter, translator, subtitles.embed/burn monkeypatched; to_cues/write_srt write into tmp_path only. Full suite passes.

Scope: only `app/screens/transcribe.py` and `tests/test_transcribe_screen.py` touched by this task, both in `files_allowed`.

## Findings

### CR-1 - Unused src_dir setup in the _run test fixture (Low, confidence 100)

- **Location:** `tests/test_transcribe_screen.py:92-93`
- **Impact:** `src_dir` is created and never used. Dead setup that suggests the tests use real source files when they do not.
- **Reproduction:** read the `env` fixture; `src_dir` is not referenced after `mkdir()`.
- **Recommended fix:** delete the two lines.

### CR-2 - Error text says "or a URL" when a URL is already present (Info, confidence 90)

- **Location:** `app/screens/transcribe.py:93`
- **Impact:** with URL + local .mp3 + Embed/Burn, the user is told "Embed/Burn needs a video file or a URL." although a URL is in the box. The real cause is that the local file wins over the URL. The exact text is mandated by acceptance criterion 1, so this is not a defect of this task.
- **Reproduction:** `_validate(stub(local_file=a.mp3, EMBED), "https://youtu.be/x")` -> that message.
- **Recommended fix (future, optional):** a clearer text such as "Embed/Burn needs a video file. Clear the local file to use the URL." (would need the acceptance/test string updated).

### CR-3 - No _run test for local video + Embed/Burn (Info, confidence 85)

- **Location:** `tests/test_transcribe_screen.py:149`
- **Impact:** the `video_src = local_file` path (local .mp4 passed to `subtitles.embed`/`burn`) is not asserted; only URL-download embed/burn is. Not required by acceptance.
- **Reproduction:** no test calls `_run` with `local_file=Path("v.mp4")` and `sub_video=EMBED`.
- **Recommended fix:** add one test asserting `env.calls["embed"][0][0] == local` and no downloader call.

## Notes for the orchestrator

- TASK-006 CR-6 still stands: `git check-ignore -v tests/test_transcribe_screen.py` -> `.gitignore:14:tests/`. The new test file is not tracked by git; needs a human decision (out of scope here).

## Coverage statement

Inspected: the full diff of `app/screens/transcribe.py` against eab24b9 (focusing on the TASK-010 change to `_validate`), the `_validate` caller in `screens/base.py`, translator constants used by `_lang_code`, and every line of `tests/test_transcribe_screen.py`. Ran all three validation commands and an in-process mutation check of the old condition. Not checked: GUI rendering or interaction, real ffmpeg/Whisper/NLLB runs, and the TASK-006 parts of the diff beyond what TASK-010 touches (already reviewed in TASK-006-code). Absence of further findings is not proof of correctness.

---
id: TASK-010
title: Fix Transcribe Embed/Burn validation with URL plus local audio and add screen logic tests
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-006"]
files_allowed: ["app/screens/transcribe.py", "tests/test_transcribe_screen.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
  - cmd: .venv/Scripts/python -c "import app.screens.transcribe"
    expect: exit 0
acceptance:
  - TranscribeScreen._validate returns "Embed/Burn needs a video file or a URL." for a local .mp3 with Subtitles on and Embed or Burn selected, both with an empty URL and with a non-empty URL; a test covers the URL + local .mp3 case for EMBED and BURN (CR-1)
  - _validate still returns None for a local video file (.mp4/.mkv) with Embed/Burn, for a URL with no local file and Embed/Burn, and for a local .mp3 with SRT file only; it still rejects no URL and no file, and no output ticked (each case has a test)
  - the condition on the former line 91 is a readable parenthesized multi-line expression with no run of embedded spaces (CR-5); behaviour otherwise unchanged
  - _lang_code tests cover ORIGINAL with a detected language and with None ("und"), Serbian (Latin) -> "sr-Latn", and every other translator.TARGETS label maps to a non-empty code without a "_" suffix
  - _run tests on a stub self show that a local file is used directly (no downloader call), URL + Embed/Burn calls downloader.download_video, and URL + SRT-only or MD/PDF-only calls downloader.download_audio_raw
  - _run tests assert output names <safe_name(title)>.<lang>.srt, .<lang>.mp4 (embed) and .<lang>.burned.mp4 (burn), that every returned path appears in the returned "Saved:" string, and that a subtitle run reports progress values that never decrease, include 0.85 and end at 1.0
  - tests are Tk-free (no CTk widget or Tk root is created; self is a types.SimpleNamespace stub), monkeypatch downloader, audio_prep, transcribe, exporter, translator and subtitles.embed/burn, and never hit the network or run real ffmpeg/Whisper/NLLB; full suite passes
max_retries: 2
attempts: 0
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Fix review findings CR-1 and CR-5 from TASK-006 so Embed/Burn validation matches the input precedence in `_run`, and add Tk-free unit tests for the Transcribe screen logic (CR-2).

## Context

- Findings: `reports/reviews/TASK-006-code.md` (CR-1 medium, CR-2 medium, CR-5 low). Source task: `tasks/TASK-006-wire-subtitles-and-translation-into-transcribe-s.md`; handoff `reports/handoffs/TASK-006.md`. Precedent for this kind of follow-up: `tasks/TASK-009-fix-subtitle-embed-stream-mapping-and-burn-proce.md`.
- CR-1 (`app/screens/transcribe.py` `_validate`, line 91): the audio-only check runs only when `not url`, but `_run` always prefers `self.local_file` over the URL. Decision: drop the `not url` term so the check is `subs and sub_video != SRT_ONLY and self.local_file and self.local_file.suffix.lower() not in VIDEO_EXTS`. Do not change the precedence in `_run`.
- CR-5: same line has ~17 embedded spaces (lost line continuation). Rewrite it as a parenthesized condition over two lines.
- CR-2: put the new tests in a new file `tests/test_transcribe_screen.py` (not `tests/test_core.py`, which TASK-008 also edits). Approach (the reviewer verified it works): `from app.screens.transcribe import TranscribeScreen, EMBED, BURN, SRT_ONLY` and call the functions unbound, e.g. `TranscribeScreen._validate(stub, url)` and `TranscribeScreen._run(stub, url, out, ...)`, where `stub` is a `SimpleNamespace` with `local_file`, `sub_var`/`md_var`/`pdf_var`/`sub_video` objects exposing `get()`, `_say`, `_prog` (recording lists) and `_lang_code=TranscribeScreen._lang_code`. Importing the module loads customtkinter but does not need a display.
- For `_run`, monkeypatch names on the `app.screens.transcribe` module: `transcribe` (return a `Transcript` of `Segment`s from `app.transcriber`, and call the progress cb), `audio_prep.prepare`, `downloader.download_video`/`download_audio_raw` (return `(path, title)`), `exporter.write_markdown`/`write_pdf`, `translator.translate_segments`, `subtitles.embed`/`burn` (return the out path). `subtitles.to_cues`/`write_srt` are pure and may write into `tmp_path`.
- Progress: assert only the subtitle-run behaviour listed in acceptance. Do not assert the final progress value of MD/PDF-only runs (CR-4 is out of scope and may change it later).
- Out of scope (do not do here): CR-3 (log saved paths early), CR-4 (progress parking at 0.6), CR-7 (burn duration), any change to `.gitignore`.
- Open note for the human (CR-6): `tests/` is listed in `.gitignore` (line 14), so the new test file will not be tracked by git. This task does not change that; it needs a human decision.
- Rules (CLAUDE.md): never touch widgets off the main thread; no new dependencies; tests never hit the network or run real ffmpeg/Whisper.

## Steps

1. Create `tests/test_transcribe_screen.py` with the `_validate` cases from acceptance, including URL + local `.mp3` + EMBED/BURN. Run it and confirm the CR-1 cases fail.
2. Add `_lang_code` tests and the `_run` routing, naming, Saved-string and progress tests with the stubs and monkeypatches described in Context.
3. Fix the `_validate` condition in `app/screens/transcribe.py` (drop `not url`, parenthesize over two lines).
4. Run every validation command and record exit codes in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when: the change needs files
outside `files_allowed`, an acceptance criterion is ambiguous, a dependency
is missing, or a validation command cannot run in this environment. Never
widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-010.md` (see templates/handoff.md)

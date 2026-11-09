---
id: TASK-006
title: Wire subtitles and translation into Transcribe screen and settings
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-003", "TASK-004", "TASK-009"]
files_allowed: ["app/screens/transcribe.py", "app/settings.py", "tests/test_core.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
  - cmd: .venv/Scripts/python -c "import app.screens.transcribe"
    expect: exit 0
acceptance:
  - Transcribe screen shows a Subtitles checkbox, a Translate-to menu (translator.TARGETS) and a Video menu (SRT file only / Embed into video (fast) / Burn into video (slow)); menus disabled while the checkbox is off
  - _validate requires at least one of Markdown/PDF/Subtitles, and Embed/Burn require a video file or URL
  - with a URL and Embed/Burn the worker uses downloader.download_video, otherwise the existing audio path
  - pipeline runs transcribe -> translate -> to_cues -> write_srt -> optional embed/burn in the worker thread only, with progress split 0.1/0.6/0.85/1.0
  - outputs are named <title>.<lang>.srt, <title>.<lang>.mp4 or <title>.<lang>.burned.mp4 via downloader.safe_name and listed in the Done message
  - settings.DEFAULTS gains subtitles=False, sub_target='Original (no translation)', sub_video='SRT file only' with a test; invalid stored values fall back to defaults
  - Markdown/PDF-only runs behave exactly as before
max_retries: 2
attempts: 0
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Let the user create (optionally translated) subtitles for a local video or URL from the Transcribe screen, saved as SRT and optionally embedded or burned into the video.

## Context

Feature plan: `C:\Users\milla\.claude\plans\analyze-this-project-and-purrfect-flute.md`.
- Existing screen: `app/screens/transcribe.py` (`_build_options`, `_validate`, `_args`, `collect_cfg`, `_run`); base class and worker/queue pattern in `app/screens/base.py`. Widgets only on the main thread; `_run` runs in the worker and may only use `self._say` / `self._prog`.
- New option row (row 2 of the options frame): `Subtitles` checkbox, `Translate to:` `CTkOptionMenu(values=list(translator.TARGETS))`, `Video:` menu with `SRT file only` / `Embed into video (fast)` / `Burn into video (slow)`; disable both menus when the checkbox is off.
- Pipeline in `_run`: (URL + Embed/Burn -> `downloader.download_video(url, tmp, cb)`; else existing `download_audio_raw`) -> `audio_prep.prepare` -> `transcribe` -> if subtitles: `translator.translate_segments(t.segments, t.language, target)` -> `subtitles.to_cues` -> `write_srt(out/<safe title>.<lang>.srt)` -> optional `embed` / `burn` (burn runs inside the temp dir, output written to `out`). Embed/Burn with a local audio-only file must be rejected in `_validate` (check extension against .mp4/.mkv/.webm/.mov/.avi).
- `<lang>` = target ISO code, or the detected `t.language` for "Original (no translation)"; "Serbian (Latin)" uses `sr-Latn`.
- Progress: download 0-0.1, transcribe 0.1-0.6, translate 0.6-0.85, embed/burn 0.85-1.0.
- Settings: add `subtitles`, `sub_target`, `sub_video` to `settings.DEFAULTS`; restore them in the screen with the same "fallback if not in options" check used for `model` / `language`. Add a settings test to `tests/test_core.py`.
- Keep the existing MD/PDF behaviour unchanged when Subtitles is off.

## Steps

1. Add the settings defaults and a failing test in `tests/test_core.py`.
2. Build the new option row and enable/disable logic.
3. Extend `_validate`, `_args`, `collect_cfg`, `_run` per Context.
4. Run every validation command; start the app (`.venv/Scripts/python main.py`) if a display is available and describe what was checked in the handoff, otherwise state it was not checked.

## Blockers

Stop and write a handoff with `status: blocked` when: the change needs files
outside `files_allowed`, an acceptance criterion is ambiguous, a dependency
is missing, or a validation command cannot run in this environment. Never
widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-006.md` (see templates/handoff.md)

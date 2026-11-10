---
id: TASK-024
title: Let Translate / Subtitles start from an existing SRT or Markdown transcript instead of Whisper
status: draft
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-022", "TASK-023"]
files_allowed: ["app/screens/transcribe.py", "tests/test_transcribe_screen.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py tests/test_transcript_import.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "The Browse file dialog (MEDIA_TYPES) gains a \"Transcript\" filter \"*.srt *.md\" between \"Audio/Video\" and \"All files\"; a picked .srt/.md file is shown and handled like any local file (URL cleared, URL-wins rule of _source_file unchanged)"
  - "TranscribeScreen._validate in transcribe mode with a local .srt or .md file (and no URL) returns \"A transcript file works only with Translate / Subtitles.\" before the Markdown/PDF check"
  - "TranscribeScreen._validate in subtitles mode with a local .srt/.md file and Embed or Burn returns the existing \"Embed/Burn needs a video file or a URL.\"; with SRT file only it returns None (Gemini key check unchanged)"
  - "TranscribeScreen._run in subtitles mode with local_file 'Talk.en.srt' never calls downloader, audio_prep or transcribe; it calls transcript_import.load(local_file), sets progress to 0.6, and then runs the existing translate -> translated document (TASK-022) -> SRT steps with title from load() and source=str(local_file); the result for target German is <out>/Talk.de.srt"
  - "The Language menu overrides the transcript language when it is not Auto (language argument of _run not None); otherwise load()'s language is used; if that is '' and the target is not Original and the engine is Local, _run raises ValueError(\"The transcript language is unknown. Choose it in the Language menu.\") before any translation; with the Gemini engine an unknown language is passed through as '' (Gemini translates, failed chunks keep their text as today)"
  - "If an output path (SRT or translated document) resolves to the same file as the input transcript, _run raises RuntimeError(\"The output would overwrite the input file. Choose another target language or output folder.\") and writes nothing"
  - "Tests on a stub self with transcript_import.load monkeypatched (and one test with a real small .srt in tmp_path) cover acceptance 2 to 6; every existing _run and _validate test passes unchanged; the full suite passes; no new dependency"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

"Translate / Subtitles" can start from an existing `.srt` or app-written `.md` transcript picked with Browse file. It then skips download and Whisper and runs translation, the translated document and the SRT as today.

## Context

Source of the request: Q3 in `tasks/TASK-019-split-the-transcribe-screen-action-into-separate.md`. The parser comes from TASK-023 (`app/transcript_import.py`: `TRANSCRIPT_EXTS`, `load(path) -> (Transcript, title)`). The translated document comes from TASK-022 (`sub_doc` in `_args`/`_run`). Read both handoffs first and use the names as built.

OPEN QUESTIONS (task stays `draft` until a human answers; the acceptance criteria assume the recommended answers. Q3a to Q3e are in TASK-023):

- Q3f. How does the user pick a transcript? Recommended: the existing Browse file button with an extra "Transcript (*.srt *.md)" filter. The file extension decides the path, and there is no new button or menu.
- Q3g. What happens when the user clicks "Transcribe" with a transcript file? Recommended: reject it with "A transcript file works only with Translate / Subtitles." Alternative: convert SRT to Markdown/PDF. That is cheap with TASK-023 and TASK-022, but it is a separate decision.
- Q3h. How do Embed/Burn find the video when the input is a transcript? Recommended: they don't in this task. A transcript input supports "SRT file only", and Embed/Burn is rejected with the existing message. Alternatives for a later task: (1) look for a sibling video `<title>.mp4/.mkv/...` next to the transcript, or (2) add a second "Video for subtitles" file picker.
- Q3i. Can target "Original" be used with a transcript input? Recommended: yes. It re-times or converts the input (for example Markdown to SRT). The overwrite guard in acceptance 6 stops `Talk.en.srt` + Original + same folder from overwriting the input.
- Q3j. Does a transcript input use the Language menu? Recommended: yes, as an override when it is not Auto (acceptance 5). Local NLLB needs a known source language. Gemini does not.

Design notes:
- Branch at the top of `_run` on `local_file and local_file.suffix.lower() in transcript_import.TRANSCRIPT_EXTS`. Build `t` there and fall through to the existing `if subs:` block, so translation, `_lang_code`, the translated document and `write_srt` are shared code, not copied.
- `want_video` must stay False for a transcript input. `_validate` already guarantees this. Do not add a video path.
- Compare paths with `Path.resolve()` and do the overwrite check before writing any output.
- `_validate` runs on the main thread. It must not read the file. It checks only the extension.
- No change to `app/transcript_import.py` (TASK-023's scope), `app/screens/base.py`, `app/settings.py` or `app/ui.py`. If the parser needs a fix, stop and report it.

## Steps

1. Confirm that Q3f to Q3j (and Q3a to Q3e in TASK-023) have been answered, that TASK-022 and TASK-023 are done, and that their handoffs match the names used here. Otherwise stop with `blocked`.
2. Add failing stub-self tests for `_validate` and `_run` with transcript inputs, as listed in acceptance 7.
3. Implement the file filter, the `_validate` rules and the `_run` branch in `app/screens/transcribe.py`.
4. Run every validation command and record the exit codes and pass counts in the handoff. The file-dialog filter is not visually verified; say so and list a manual check (pick a `.srt`, translate to German, open the folder) under `next_steps`.

## Blockers

Stop and write a handoff with `status: blocked` when the open questions are unanswered or the answers contradict the acceptance criteria, TASK-022 or TASK-023 is not done, the change needs files outside `files_allowed`, or a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-024.md` (see templates/handoff.md)

---
id: TASK-019
title: Split the Transcribe screen action into separate Transcribe and Translate / Subtitles buttons
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: ["TASK-018"]
files_allowed: ["app/screens/base.py", "app/screens/transcribe.py", "tests/test_transcribe_screen.py", "tests/test_gemini.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py tests/test_gemini.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "The Transcribe screen shows two action buttons side by side, \"Transcribe\" and \"Translate / Subtitles\"; both are disabled while a job runs and re-enabled on done or error (Screen._set_busy toggles every button in self.action_buttons); the Audio and Video screens still show one button with unchanged text and behaviour"
  - "TranscribeScreen._args() in transcribe mode returns subs=False and md/pdf from the checkboxes; in subtitles mode it returns subs=True, md=False and pdf=False (see open question Q1), with model, source file, language, target, video mode, engine, key and gemini_model as today; the mode is snapshotted on the main thread before the worker starts"
  - "TranscribeScreen._validate in transcribe mode: no URL and no file gives \"Paste a URL or choose a local file.\"; neither Markdown nor PDF ticked gives \"Tick Markdown and/or PDF.\"; it never returns GEMINI_HINT or the Embed/Burn message, even with Gemini selected and no key"
  - "TranscribeScreen._validate in subtitles mode: Embed/Burn with an audio local file and empty URL gives \"Embed/Burn needs a video file or a URL.\"; Gemini engine + non-Original target + no key gives GEMINI_HINT; Markdown/PDF unticked is accepted; URL-wins behaviour of _source_file from TASK-017 is kept"
  - "The Subtitles checkbox is removed; the Translate to, Video and Translator menus are always enabled; _gemini_missing no longer depends on a checkbox; collect_cfg no longer writes the \"subtitles\" key (app/settings.py is not changed; the unused default is harmless)"
  - "The body of TranscribeScreen._run is unchanged (it already supports md/pdf/subs as separate flags) and every existing _run test passes unchanged"
  - "New stub-self tests cover _args and _validate in both modes and Screen._set_busy toggling all action_buttons; in tests/test_gemini.py only test_validate_blocks_gemini_without_key is updated (set subtitles mode on its stub instead of sub_var); the full suite passes; no new dependency"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

The Transcribe screen has two action buttons: "Transcribe" writes only the Markdown/PDF transcript, and "Translate / Subtitles" runs the subtitle path (optional translation, SRT, embed/burn).

## Context

OPEN QUESTIONS (task stays `draft` until a human answers; the recommended answer is what the acceptance criteria above assume):

- Q1. Should "Translate / Subtitles" also write the original-language Markdown/PDF when those boxes are ticked? Recommended: no. Each button produces only its own output, and the MD/PDF checkboxes belong to "Transcribe". If yes, change acceptance 2 to pass md/pdf from the checkboxes in both modes, and drop "Markdown/PDF unticked is accepted" from acceptance 4.
- Q2. Should translation also produce a translated transcript document (MD/PDF in the target language), not only an SRT? Today translation feeds only the SRT. Recommended: not in this task. If wanted, it is a separate follow-up task (exporter and `_run` change) planned after this one.
- Q3. Should "Translate / Subtitles" accept an existing transcript or SRT instead of running Whisper again? Recommended: no. It transcribes the URL or local file as today. Importing transcripts would be a new input path and a separate task.
- Q4. Remove the "Subtitles" checkbox, because the second button replaces it? Recommended: yes (acceptance 5).
- Q5. Button labels "Transcribe" and "Translate / Subtitles"? Is target "Original" (SRT in the spoken language, no translation) allowed with the second button? Recommended: these labels, and Original allowed.

ANSWERS (user, 2026-11-10): Q1 no; Q2 and Q3 not in this task (follow-up tasks to be planned afterwards); Q4 remove the checkbox; Q5 labels as proposed, Original allowed. The acceptance criteria above match these answers.

Current code (after TASK-018):
- `app/screens/base.py`: one `self.button` (row 3, `command=self._start`); `_set_busy` toggles only it. `_start()` validates via `self._validate(url)`, snapshots `self._args()` on the main thread and starts `_worker`.
- `app/screens/transcribe.py`: `button_text = "Transcribe"`; the `sub_var` checkbox gates subtitles (`_toggle_subs`, `_gemini_missing`, `_validate`, `_args`, `collect_cfg`). `_run(url, out, model, md, pdf, local_file, language, subs, target, sub_video, engine, api_key, gemini_model)` already handles md/pdf/subs independently. URL + Embed/Burn downloads video, otherwise audio.

Design (assuming the recommended answers):
- `base.py`: put the action button(s) in a frame at row 3 built by a hook `_build_actions(self, parent) -> list` (default: the single `self.button` as today, `command=self._start`). Store the result in `self.action_buttons`; `_set_busy` sets the state of every button in it. Keep `self.button` for the default case. No other base behaviour changes (playlist flow, `_poll`, DoneDialog from TASK-018).
- `transcribe.py`: constants `MODE_TRANSCRIBE = "transcribe"` and `MODE_SUBTITLES = "subtitles"`, attribute `self.mode` (default `MODE_TRANSCRIBE`). `_build_actions` creates two buttons in one row (equal weight); each command calls `self._start_mode(mode)`, which sets `self.mode` and then calls `self._start()`. `_validate` and `_args` branch on `self.mode`. Remove `sub_var`, the checkbox and `_toggle_subs`; the subtitle and translator menus stay enabled. `_gemini_missing()` becomes: engine is Gemini, target is not Original, and there is no key.
- Do not change `_run`'s body, `app/settings.py`, `app/ui.py` or other screens.
- Tests: extend the stub helpers in `tests/test_transcribe_screen.py` (`make_stub` gains `mode`; replace `sub_var` uses). Existing `_validate` tests that rely on `subs=True` move to subtitles mode with the same expected messages; `test_validate_requires_an_output` becomes the transcribe-mode "Tick Markdown and/or PDF." case.

## Steps

1. Confirm that Q1 to Q5 have been answered and the acceptance criteria match the answers. Otherwise stop with `blocked`.
2. Read `app/screens/base.py`, `app/screens/transcribe.py`, `tests/test_transcribe_screen.py` and `tests/test_gemini.py::test_validate_blocks_gemini_without_key`.
3. Update or add failing tests for both modes, `_set_busy` and the Gemini validate test.
4. Add `_build_actions` / `action_buttons` to `base.py`.
5. Implement the modes, the two buttons and the checkbox removal in `transcribe.py`.
6. Run every validation command and record exit codes and pass counts in the handoff. The layout is not visually verified by tests; say so and list a manual check under `next_steps`.

## Blockers

Stop and write a handoff with `status: blocked` when the open questions are unanswered or the answers contradict the acceptance criteria, the change needs files outside `files_allowed` (for example `app/settings.py`, `app/exporter.py` for Q2), or a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-019.md` (see templates/handoff.md)

---
id: TASK-017
title: Fix stale local file overriding a new URL on the Transcribe screen
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: []
files_allowed: ["app/screens/transcribe.py", "tests/test_transcribe_screen.py", "tests/test_gemini.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_transcribe_screen.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "TranscribeScreen._source_file(url) returns None when url is non-empty and self.local_file when url is empty"
  - "_validate(url) uses _source_file(url): an audio local file (a.mp3) + URL + Embed/Burn returns None; the same file with url \"\" still returns \"Embed/Burn needs a video file or a URL.\"; no URL and no file still returns \"Paste a URL or choose a local file.\""
  - "_args() passes _source_file(self.url.get().strip()) as the 4th element: with local_file set and a non-empty URL it is None; with an empty URL it is the local file; _run itself is unchanged"
  - "_pick_file clears the URL entry after a file is chosen (cancelled dialog changes nothing)"
  - "a handler bound to the URL entry (<KeyRelease> and <<Paste>>) resets local_file to None and file_lbl text to NO_FILE_TEXT when the URL text is non-empty and local_file is set; with an empty URL nothing changes; the URL text is never deleted by it"
  - "test_validate_rejects_audio_with_embed_burn is updated to the empty-URL case only; new stub-self tests cover _source_file, URL-wins _validate, _args and the URL handler; GEMINI_API_KEY is unset in the _args test; the full suite passes; no new dependency; app/screens/base.py is unchanged"
max_retries: 2
attempts: 1
created: 2026-11-10
updated: 2026-11-10
blocked_reason: null
---

## Objective

On the Transcribe screen, the most recently entered source wins: a non-empty YouTube URL is always used instead of a local file picked earlier.

## Context

- Bug: after transcribing a file picked with "Browse file", `TranscribeScreen.local_file` stays set (only the Clear button resets it). Pasting a YouTube URL and clicking Transcribe then transcribes the old file again, because `_run` (`app/screens/transcribe.py:170`) checks `if local_file:` first and `_args` (line 139) passes `self.local_file` unconditionally. `_validate` (line 128) also uses the stale file.
- Design:
  - Add `_source_file(self, url) -> Path | None`: `return None if url else self.local_file`.
  - `_validate`: replace `self.local_file` with `self._source_file(url)` in both checks.
  - `_args`: replace `self.local_file` with `self._source_file(self.url.get().strip())`.
  - `_pick_file`: after a file is chosen, `self.url.delete(0, "end")`.
  - Add `_on_url_change(self, _event=None)`: if `self.url.get().strip()` and `self.local_file`, set `self.local_file = None` and `self.file_lbl.configure(text=NO_FILE_TEXT)`. Bind it in `__init__` after `super().__init__(...)` (where `self.url` exists) to `<KeyRelease>` and `<<Paste>>`. For `<<Paste>>`, the entry text changes after the event, so schedule the check with `self.after_idle(self._on_url_change)`. Main thread only.
  - Do not change `app/screens/base.py`, `_run`, or the playlist flow.
- Tests: follow the stub-self pattern in `tests/test_transcribe_screen.py` (`make_stub`, `Var`). For `_validate`, set `stub._source_file = lambda u: TranscribeScreen._source_file(stub, u)`. For the `_args` stub, provide `model`, `md_var`, `pdf_var`, `language` (a value in `tmod.LANGUAGES`), `sub_var`, `sub_target`, `sub_video`, `engine`, `cfg={}`, `url` (with `get`) and `_source_file`; `monkeypatch.delenv("GEMINI_API_KEY", raising=False)`. For `_on_url_change`, the stub's `file_lbl.configure` records `text`.
- Scope widened (user decision, 2026-11-10): `tests/test_gemini.py` is allowed only to add `_source_file` to the `_validate` stub used by `test_validate_blocks_gemini_without_key` (for example `stub._source_file = lambda u: TranscribeScreen._source_file(stub, u)`). Make no other change there.
- No docs change: data flow is unchanged and only input precedence changes.

## Steps

1. Read `app/screens/transcribe.py` and `tests/test_transcribe_screen.py`.
2. Add failing tests (see acceptance) and update `test_validate_rejects_audio_with_embed_burn`.
3. Implement `_source_file`, update `_validate` and `_args`, clear the URL in `_pick_file`, and add and bind `_on_url_change`.
4. Run every validation command and record exit codes and pass counts in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when the change needs files outside `files_allowed` (for example `app/screens/base.py`), an acceptance criterion is ambiguous, or a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-017.md` (see templates/handoff.md)

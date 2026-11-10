---
id: TASK-018
title: Add an Open folder button to the Done popup on the Audio, Video and Transcribe screens
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: []
files_allowed:
  - app/screens/done_dialog.py
  - app/screens/base.py
  - app/screens/audio.py
  - app/screens/video.py
  - app/screens/transcribe.py
  - tests/test_done_dialog.py
  - tests/test_transcribe_screen.py
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_done_dialog.py tests/test_transcribe_screen.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "done_dialog.done_payload(result) returns (message, path): a plain str \"x\" gives (\"x\", None); a tuple (\"x\", p) gives (\"x\", Path(p)); (\"x\", None) gives (\"x\", None); None or \"\" gives (\"Finished.\", None)"
  - "done_dialog.open_folder(path, startfile=f, popen=p) with injected fakes: an existing file calls p once with the string explorer /select,\"<absolute file path>\" and not f, and returns True; an existing directory calls f(str(dir)) and returns True; a missing file whose parent folder exists calls f(str(parent)) and returns True; a path whose folder does not exist returns False and calls neither; with no injected fakes it uses os.startfile (looked up at call time, so importing the module works off Windows) and subprocess.Popen"
  - "AudioScreen._run and VideoScreen._run return (message, path), where message is exactly the current text (\"Audio saved:\\n<path>\" / \"Video saved:\\n<path>\") and path is the file returned by downloader.download_audio / download_video (tested on a stub self with the downloader monkeypatched)"
  - "Screen._playlist_worker puts (\"done\", (msg, out)) on the queue, where msg is the current playlist summary text (including the Failed list) and out is the playlist folder Path; the error path still puts (\"error\", str)"
  - "TranscribeScreen._run returns (text, saved[-1]) where text is the current \"Saved:\\n...\" string; the existing _run tests in tests/test_transcribe_screen.py are updated to read result[0] and still assert the same content, including that the Gemini key never appears in it"
  - "Screen._poll handles (\"done\", val) by calling done_payload(val) and opening DoneDialog(self, message, path) instead of messagebox.showinfo; a stub-self test with DoneDialog monkeypatched in app.screens.base shows it is called once with the message and path, and _set_busy(False), bar.set(1) and the \"Done.\" log line still happen; the (\"error\", ...) branch still uses messagebox.showerror"
  - "DoneDialog (CTkToplevel, main thread only) shows the message, an \"Open folder\" button only when path is not None, and an \"OK\" button that closes it; Enter and Escape also close it; it is transient to the app window and grabs focus; clicking Open folder calls open_folder(path) and, when that returns False, shows messagebox.showwarning(\"Open folder\", \"Folder not found:\\n<folder>\") and keeps the dialog open"
  - "worker threads still only put tuples on the queue; open_folder runs only from the dialog button command (main thread); no new dependency; error popups, progress and log behaviour are unchanged; the full suite passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

When a job finishes on the Audio, Video or Transcribe screen, the completion popup has an "Open folder" button that opens Explorer on the output folder with the new file selected.

## Context

- Today `Screen._poll` (`app/screens/base.py`, "done" branch) shows `messagebox.showinfo("Done", val or "Finished.")`, where `val` is the string returned by `_run` (`app/screens/audio.py`, `app/screens/video.py`, `app/screens/transcribe.py`) or built by `Screen._playlist_worker`. No path is passed separately.
- Design (decided):
  - New module `app/screens/done_dialog.py`:
    - `done_payload(result) -> tuple[str, Path | None]` (pure; accepts the old str form and the new `(message, path)` tuple, so a screen that still returns a str keeps working without a button).
    - `open_folder(path, *, startfile=None, popen=None) -> bool` (pure apart from the injected calls; see acceptance). For a file use `popen(f'explorer /select,"{path}"')` (a single string, not a list: explorer parses `/select,` itself and list quoting breaks paths with spaces). Do not check explorer's exit code (it returns 1 even on success). Resolve `startfile = startfile or getattr(os, "startfile", None)` at call time.
    - `DoneDialog(ctk.CTkToplevel)`: title "Done", message label with wraplength, buttons "Open folder" (only when a path is given) and "OK". Use `transient(master.winfo_toplevel())`, `grab_set()`, `focus()`, and bind `<Return>`/`<Escape>` to close. Keep it small; no layout logic worth unit-testing.
  - `base.py`: `_poll` done branch uses `done_payload` + `DoneDialog`. `_playlist_worker` puts `("done", (msg, out))` (the folder itself; `open_folder` opens a directory directly). Import `DoneDialog` at module level in `base.py` so tests can monkeypatch `app.screens.base.DoneDialog`. The warning popup in `_start`, the playlist error and the error branch keep using `messagebox`.
  - `audio.py` / `video.py`: `_run` returns `(message, path)`; `_run_item` is unchanged.
  - `transcribe.py`: `_run` returns `(text, saved[-1] if saved else None)`. All outputs are written to the same `out` folder, and the last one is the most final artifact (video, else SRT, else PDF/MD). Change only the `return` line; the TASK-019 split-button work builds on this file afterwards.
- Tests: new `tests/test_done_dialog.py` for `done_payload`, `open_folder` (use `tmp_path` and fake `startfile`/`popen` recorders), Audio/Video `_run` (stub self with `_say`/`_prog`, monkeypatch `app.downloader.download_audio`/`download_video`), `_playlist_worker` (stub with a real `queue.Queue`, `_say`, `_prog`, `_run_item`) and `_poll` (stub with `q`, `_set_busy`, `bar`, `_log`, `after`; monkeypatch `base.DoneDialog` and `base.messagebox`). Follow the stub-self style of `tests/test_transcribe_screen.py`. Do not create real Tk windows in tests.
- Windows-only app; `tests/` and `docs/` are gitignored by project choice (do not change that).
- Docs are updated separately in TASK-020.

## Steps

1. Read `app/screens/base.py`, `audio.py`, `video.py`, the end of `transcribe.py::_run`, and `tests/test_transcribe_screen.py`.
2. Write failing tests in `tests/test_done_dialog.py` for the acceptance criteria; update the `_run` result assertions in `tests/test_transcribe_screen.py` to `result[0]`.
3. Add `app/screens/done_dialog.py` (`done_payload`, `open_folder`, `DoneDialog`).
4. Change the `_run` return values in audio/video/transcribe and the done payload in `_playlist_worker`.
5. Replace the `messagebox.showinfo` call in `_poll` with `DoneDialog`.
6. Run every validation command and record the exit codes and pass counts in the handoff. The dialog itself is not visually verified by tests; say so in the handoff and list a manual check (run a short audio download, click Open folder) under `next_steps`.

## Blockers

Stop and write a handoff with `status: blocked` when the change needs files outside `files_allowed` (for example `app/ui.py` or `app/downloader.py`), an acceptance criterion is ambiguous, or a validation command cannot run in this environment. Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-018.md` (see templates/handoff.md)

---
task: TASK-018
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/screens/done_dialog.py
  - app/screens/base.py
  - app/screens/audio.py
  - app/screens/video.py
  - app/screens/transcribe.py
  - tests/test_done_dialog.py
  - tests/test_transcribe_screen.py
not_checked:
  - real explorer.exe / os.startfile calls (would open Explorer on the host)
  - DoneDialog appearance in the running app
findings:
  - id: CR-1
    severity: low
    title: No test asserts the path element (saved[-1]) returned by TranscribeScreen._run
    location: app/screens/transcribe.py:229
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: open_folder default bindings and DoneDialog._open warning path are untested
    location: app/screens/done_dialog.py:30
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: OSError from Popen/startfile in the Open folder button is not caught
    location: app/screens/done_dialog.py:68
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: _poll reschedule is not in a finally block (pre-existing)
    location: app/screens/base.py:173
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
---

## Summary

The change meets every acceptance criterion. Only the consumer of the done payload is Screen._poll (grep over app/), so the return-type change breaks no callers. Worker threads still only queue tuples; open_folder runs only from the button command. No new dependency. CR-1 relates to the TranscribeScreen._run acceptance item; CR-2 to the open_folder default-binding item.

## Evidence (re-run by reviewer)

- pytest tests/test_done_dialog.py tests/test_transcribe_screen.py -q: exit 0, 62 passed (matches handoff)
- pytest -q: exit 0, 191 passed, 2 skipped (matches handoff)
- Real-Tk probe (stdin script, no files written): title Done; buttons Open folder + OK with a path, only OK without; auto-sized 451x134; transient to root; Open folder on a missing folder calls showwarning with Folder not found and the folder, and the dialog stays open; grab_current is the dialog after 300 ms; Escape and Return destroy it; destroying before the deferred _take_focus raises no Tcl error.

## Findings

### CR-1 - No test asserts the TranscribeScreen._run path element (Low, 95)

- **Location:** app/screens/transcribe.py:229; tests/test_transcribe_screen.py:231-284
- **Impact:** The updated tests read result[0] only. A change to saved[0], or dropping the path, passes all tests while the button selects the wrong file or vanishes.
- **Reproduction:** Change the second element to saved[0] and run the transcribe tests: all pass.
- **Recommended fix:** Assert run(...)[1] == mp4 (embed test), == burned (burn test), == env.out / "My Title.pdf" (md+pdf test).

### CR-2 - open_folder default bindings and DoneDialog._open untested (Low, 90)

- **Location:** app/screens/done_dialog.py:30, :35, :68-70
- **Impact:** The code correctly resolves os.startfile and subprocess.Popen at call time, but no test covers it, so a refactor binding them at import time or dropping the fallback goes unnoticed. The warning branch in _open was only checked by my probe.
- **Reproduction:** Replace line 35 with startfile = startfile or None and run the suite: it passes.
- **Recommended fix:** Monkeypatch os.startfile (raising=False) and subprocess.Popen with recorders and call open_folder without keyword arguments; optionally test _open on a SimpleNamespace stub with done_dialog.messagebox.showwarning patched.

### CR-3 - OSError from Popen/startfile not caught (Info, 80)

- **Location:** app/screens/done_dialog.py:68-70
- **Impact:** If explorer or startfile raises (access denied, share dropped after the existence check), Tk prints a traceback and the user sees nothing. Rare on Windows; not required by the task.
- **Reproduction:** Inject a startfile that raises OSError; the exception leaves the button command.
- **Recommended fix:** Optional: catch OSError in _open and show it via messagebox.showwarning.

### CR-4 - _poll reschedule not in finally (Info, 85, pre-existing)

- **Location:** app/screens/base.py:173-195
- **Impact:** If the done branch raises (now a CTkToplevel constructor instead of showinfo), self.after(100, self._poll) is skipped and the screen stops polling until restart. Pre-existing structure, slightly larger surface; not a regression in practice.
- **Reproduction:** Patch base.DoneDialog to raise and call Screen._poll(stub): after is never called.
- **Recommended fix:** Optional, separate task: move the after call into a finally block.

## Questions

- The probe placed DoneDialog at +26+26 (window manager default), not centred over the app as showinfo was. PlaylistDialog does the same; the manual check in the handoff next_steps should confirm it is acceptable.

## Coverage statement

Inspected: the full diff vs 1668a3f for base/audio/video/transcribe, all of done_dialog.py, both test files (gitignored, so read directly), PlaylistDialog for convention, downloader return paths, and CTkToplevel.__init__ sizing in customtkinter 6.0.0. Ran: both validation commands and a real-Tk probe. Not checked: real Explorer/startfile calls, themed appearance in the running app, two screens finishing at once (grab contention). No findings beyond these does not prove correctness.

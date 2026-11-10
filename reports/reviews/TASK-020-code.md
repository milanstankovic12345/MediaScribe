---
task: TASK-020
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - tasks/TASK-020-document-the-open-folder-done-dialog-and-the-spl.md
  - reports/handoffs/TASK-018.md
  - reports/handoffs/TASK-019.md
  - reports/handoffs/TASK-020.md
  - CLAUDE.md
  - docs/blueprint.md
  - docs/tasks.md
  - app/screens/done_dialog.py
  - app/screens/base.py
  - app/screens/transcribe.py
  - app/screens/audio.py
  - app/screens/video.py
  - tests/test_done_dialog.py
  - tests/test_transcribe_screen.py
not_checked:
  - Pre-edit text of the gitignored docs (no baseline to diff docs/tasks.md against)
  - Running app and Explorer behaviour (no window launched)
findings:
  - id: CR-1
    severity: medium
    title: Blueprint Local file line still says "(and subtitles, if ticked)" from the removed Subtitles checkbox
    location: docs/blueprint.md:35
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: Threading paragraph says a missing folder shows a warning, but a missing folder opens its parent
    location: docs/blueprint.md:39
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: CLAUDE.md says a plain str done value shows no button, but the OK button is still shown
    location: CLAUDE.md:21
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: CLAUDE.md Transcribe pipeline bullet and Gotchas Tests bullet not refreshed
    location: CLAUDE.md:23
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
---

## Summary

The docs describe TASK-018 and TASK-019 accurately overall. I checked each claim against the working-tree code and found it correct: the (message, path) done payload and plain-str fallback; the path each screen sends (the saved file for Audio/Video, the last saved file for Transcribe, the playlist folder for the playlist worker); done_payload, open_folder and DoneDialog; _build_actions, action_buttons and _set_busy; the mode-driven _validate and _args; MD/PDF being ignored in Translate / Subtitles mode; Original being allowed; the Gemini block applying only to the second button; and the button labels. The "any combination" sentence is gone. Round 5 (items 30 and 31, both ticked) was added. README.md, docs/prd.md and docs/techstack.md are untouched, and there are no emojis.

Validation re-run in this session:
- doc marker check (python -c ...) gave exit 0
- .venv/Scripts/python -m pytest -q gave exit 0, 196 passed and 2 skipped (same as the handoff)
- probe: open_folder(tmp / "Missing Playlist", startfile=..., popen=...) returned True and opened the parent tmp dir

## Findings

### CR-1: Stale Subtitles-checkbox wording on the Local file line (Medium, confidence 95)

- **Location:** docs/blueprint.md:35, which reads "Local file: path → transcriber → exporter (and subtitles, if ticked)."
- **Impact:** The checkbox no longer exists (line 32 says so). In Translate / Subtitles mode no MD/PDF is written, because _args passes md and pdf as False. The line contradicts the code and line 32, and acceptance 3 requires the checkbox wording to be updated.
- **Reproduction:** grep -n "if ticked" docs/blueprint.md matches line 35. A local file run with the Translate / Subtitles button writes only the SRT and the optional video, with no .md or .pdf.
- **Recommended fix:** Change the line to "Local file: path → audio_prep → transcriber → exporter (Transcribe button) or translation, SRT and embed/burn (Translate / Subtitles button; the local file is the video source)."

### CR-2: Missing-folder behaviour misdescribed (Low, confidence 95)

- **Location:** docs/blueprint.md:39 (also "missing folder -> False" at line 9)
- **Impact:** open_folder falls back to folder_of(path). A missing path that is not a file opens its parent folder. A missing playlist folder (all items failed, or the folder was deleted) therefore opens the screen output folder without a warning. The warning appears only when the parent is missing too. This relates to acceptance 6 (only existing behaviour documented).
- **Reproduction:** The probe above returned True and called startfile on the parent.
- **Recommended fix:** Change the wording to "a missing file or folder opens its parent folder; if that is missing too, a warning is shown".

### CR-3: "shows no button" (Low, confidence 95)

- **Location:** CLAUDE.md:21
- **Impact:** DoneDialog always shows OK. Only Open folder is omitted when path is None (done_dialog.py:53-56). The blueprint words this correctly.
- **Recommended fix:** Change the text to "shows no Open folder button".

### CR-4: Adjacent CLAUDE.md bullets (Info, confidence 90)

- **Location:** CLAUDE.md:23 and CLAUDE.md:40
- **Impact:** The Transcribe pipeline bullet still ends in write_markdown / write_pdf unconditionally (line 24 qualifies it). The Gotchas Tests bullet omits test_done_dialog.py. Neither bullet is named in the acceptance criteria.
- **Recommended fix:** Optionally add "(Transcribe button only)" to line 23 and add test_done_dialog.py to line 40.

## Acceptance criteria

1. Module map has done_dialog.py: met (blueprint:9).
2. Threading paragraph covers the payload, the str fallback and the playlist folder: met (blueprint:39), with CR-2 noted.
3. Data flow, Subtitles note, UI layout and the hook in the app/screens line: met for the named sections (blueprint:18, 25-32, 37). CR-1 is a leftover.
4. CLAUDE.md Architecture bullets: met (lines 21, 24, 25, 26), with CR-3 noted.
5. tasks.md Round 5, items 30 and 31: met. Earlier items look intact, but there was no baseline to diff.
6. Only existing behaviour, excluded files untouched, validation passes: met apart from the CR-1 and CR-2 wording.

## Coverage statement

Inspected: CLAUDE.md (Architecture and Gotchas), all of docs/blueprint.md, the docs/tasks.md tail, the git diff of app/screens/ against 1668a3f, done_dialog.py, the transcribe and base worker/poll/validate/args code, and the test names in test_done_dialog.py and test_transcribe_screen.py. Ran both validation commands and an open_folder probe. Not checked: the pre-edit doc text (gitignored, no baseline) and the running UI or Explorer (no window launched).

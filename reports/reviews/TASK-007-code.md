---
task: TASK-007
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - CLAUDE.md (full file, untracked; read directly)
  - docs/techstack.md, docs/blueprint.md, docs/prd.md, docs/tasks.md (full files, untracked; read directly)
  - app/translator.py (full; MODEL_REPO, MODEL_REVISION, _assets/_models, _fetch outside try, shared transcriber._cuda_broken, cyr_to_lat, TARGETS, WHISPER_TO_NLLB)
  - app/subtitles.py (full; write_srt utf-8-sig, embed -c copy + mov_text, burn subs.srt + cwd=tmp)
  - app/screens/transcribe.py (full; _validate, _lang_code, _run progress split and output names)
  - app/settings.py (subtitles defaults)
  - requirements.txt, requirements-dev.txt, run.bat (sentencepiece listed; run.bat installs only on first run)
  - tests/ listing and tests/test_e2e_subtitles.py skip gate (YT_TOOL_E2E == "1")
  - tasks/*.md status fields (to check the Round 4 ticks against done tasks)
  - reports/handoffs/TASK-007.md
not_checked:
  - Real NLLB translation (sentencepiece not installed in .venv; confirmed ModuleNotFoundError)
  - Opt-in e2e tests with real ffmpeg (not re-run by me; validation command does not require it)
  - Upstream licence of the NLLB model (CC-BY-NC claim not re-checked online)
  - Running the GUI / visual check of the Subtitles row
findings:
  - id: CR-1
    severity: low
    title: Docs do not say translation only accepts 13 source languages
    location: docs/prd.md:17
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: info
    title: Edited blueprint local-file flow line still omits audio_prep
    location: docs/blueprint.md:29
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: CLAUDE.md settings bullet does not list the new subtitles config keys
    location: CLAUDE.md:27
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: Pre-existing techstack PDF row (DejaVu) contradicts CLAUDE.md (Arial/Segoe UI)
    location: docs/techstack.md:13
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
---

## Summary

All four acceptance criteria are met. I checked each technical claim in the docs against the code and found them accurate: the pinned model repo and revision, `_assets`/`_models` keys, `_cuda_broken` being shared and only set on GPU inference/model-construction failures (`_fetch` sits outside the `try`), Serbian Cyrillic-only plus `cyr_to_lat`, `subs.srt` + `cwd=tmp` in `burn`, UTF-8 BOM SRT, `.mp4`/`.burned.mp4` names, the 0/0.1/0.6/0.85/1.0 progress split, the URL path that downloads video for Embed/Burn, and the `YT_TOOL_E2E=1` gate. Round 4 ticks 20-26 match tasks that are `done` (002-006, 009, 010). Item 27 ticks this task while it is still in `review`, which is fine if it is accepted. Item 28 is correctly left open. Only a low and some info findings remain.

## Findings

### CR-1 — Docs do not say translation only accepts 13 source languages (Low, confidence 90)

- **Location:** `docs/prd.md:17`; also relevant to the CLAUDE.md Gotchas and the techstack Translation row
- **Impact:** `translator.translate_segments` raises `ValueError("Translation from language 'xx' is not supported.")` when the Whisper-detected language is not in `WHISPER_TO_NLLB` (en, sr, hr, bs, de, fr, es, it, ru, pt, nl, pl, tr). None of the docs mention this limit. A user or a future agent reading the PRD ("optionally translated offline into a chosen language") would expect any source language to work.
- **Reproduction:** transcribe a Japanese video (`t.language == "ja"`) with Subtitles ticked and target "English". `app/translator.py:132-134` raises after MD/PDF have already been written, and the run ends in an error.
- **Recommended fix:** add one sentence to the PRD and a Gotchas bullet: "Translation source languages are limited to `WHISPER_TO_NLLB` (13 languages); other detected languages raise an error. 'Original' always works."

### CR-2 — Edited blueprint local-file flow line still omits audio_prep (Info, confidence 95)

- **Location:** `docs/blueprint.md:29`
- **Impact:** "Local file: path → transcriber → exporter (and subtitles, if ticked)". In fact `_run` also sends local files through `audio_prep.prepare` (`app/screens/transcribe.py:138`). The inaccuracy existed before this task, but the task edited this line and kept it.
- **Recommended fix:** "Local file: path → audio_prep → transcriber → exporter (and subtitles, if ticked; the file itself is the video for Embed/Burn)."

### CR-3 — CLAUDE.md settings bullet does not list the new subtitles config keys (Info, confidence 95)

- **Location:** `CLAUDE.md:27`
- **Impact:** `app/settings.py:13-15` adds `subtitles`, `sub_target` and `sub_video` defaults, and `TranscribeScreen.collect_cfg` saves them. The settings bullet does not mention them. Acceptance does not require this, so this is only a completeness gap.
- **Recommended fix:** append "Transcribe also stores `subtitles`, `sub_target`, `sub_video`."

### CR-4 — Pre-existing techstack PDF row (DejaVu) contradicts CLAUDE.md (Arial/Segoe UI) (Info, confidence 85)

- **Location:** `docs/techstack.md:13`
- **Impact:** This existed before the task and is outside its scope. The techstack row says "fpdf2 + DejaVu font", while the CLAUDE.md Gotchas say `write_pdf` uses Arial or Segoe UI from `%WINDIR%\Fonts`. I did not re-read `exporter.py` to settle which is right, hence confidence 85.
- **Recommended fix:** align the techstack row with `exporter.write_pdf` in a later docs pass.

## Validation re-run

- `.venv/Scripts/python -m pytest -q` → exit 0, `98 passed, 2 skipped in 1.00s` (matches the handoff).
- `.venv/Scripts/python -c "import sentencepiece"` → `ModuleNotFoundError` (confirms the handoff's concern that the real NLLB path is unverified here).
- `importlib.metadata.requires('faster-whisper')` → includes `ctranslate2>=4.0` and `huggingface-hub>=0.21`, which supports the claim that `sentencepiece` is the only new package.

## Notes for orchestrator (outside review scope)

- `CLAUDE.md`, `docs/` and `tests/` are matched by `.gitignore` lines 12-14 (`git check-ignore -v` confirmed). This means the doc edits **and the feature's test files** (`test_subtitles.py`, `test_translator.py`, `test_transcribe_screen.py`, `test_e2e_subtitles.py`) are not under version control. The user needs to decide this.

## Coverage statement

Inspected: every file the task changed (read in full, since git diff is empty for ignored files), the code they describe (`translator.py`, `subtitles.py`, `screens/transcribe.py`, `settings.py`), requirements files, `run.bat`, the e2e skip gate, and task statuses. Ran: the validation pytest, a sentencepiece import check, and a faster-whisper dependency query. Not checked: real NLLB/ffmpeg runs, the opt-in e2e suite, the upstream licence of the NLLB model, `exporter.py` (CR-4), and the GUI. A review with no blocking findings does not prove that the docs are complete or that the feature works end to end.

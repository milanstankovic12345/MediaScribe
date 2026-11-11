---
task: TASK-023
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/transcript_import.py
  - tests/test_transcript_import.py
  - app/exporter.py, app/subtitles.py, app/transcriber.py, app/translator.py, app/screens/transcribe.py (related functions)
not_checked:
  - UI wiring (TASK-024)
  - real 20 MB file (monkeypatched test only)
findings:
  - id: CR-1
    severity: medium
    title: Markdown header language not normalized (sr-Latn / und from app-written docs)
    location: app/transcript_import.py:127
    confidence: 92
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: SRT timing lines with trailing position coordinates are dropped
    location: app/transcript_import.py:33
    confidence: 88
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: The an8 brace test uses a non-raw string, so it contains BEL instead of a backslash
    location: tests/test_transcript_import.py:23
    confidence: 97
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: load raises OSError for missing files and the Markdown title is unsanitized (TASK-024 contract)
    location: app/transcript_import.py:113
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-5
    severity: info
    title: UTF-16 SRT reports no segments found instead of an encoding error
    location: app/transcript_import.py:97
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
---

## Validation re-run

- `.venv/Scripts/python -m pytest tests/test_transcript_import.py -q`: exit 0, 20 passed.
- `.venv/Scripts/python -m pytest -q`: exit 0, 225 passed, 2 skipped. Both match the handoff.
- An inline repro script confirmed every finding. Adversarial 100-200 KB inputs took 15 ms or less, so the regexes are linear.

## Findings

### CR-1 (Medium, 92)
- **Location:** app/transcript_import.py:127. parse_markdown line 74 keeps the header verbatim.
- **Impact:** TASK-022 translated docs are written as Transcript(segs, lang) with lang from _lang_code, which can be sr-Latn or und, so their header reads "- Language: sr-Latn" or "- Language: und". load maps sr-Latn to sr and und to empty only for the filename suffix, and the header wins. Loading the app's own Serbian Latin document gives language "sr-Latn". With Auto language in TASK-024, translate_segments then raises "Translation from language sr-Latn is not supported" (reproduced).
- **Reproduction:** Write to_markdown(Transcript([Segment(0,1,"Zdravo")], "sr-Latn"), "Talk", "src") to Talk.sr-Latn.md. load() returns language "sr-Latn" instead of "sr". An und header returns "und" instead of "".
- **Fix:** Set lang = language if language is not None else file_lang, then lang = {"sr-Latn": "sr", "und": ""}.get(lang, lang). Add a test for each header.

### CR-2 (Low, 88)
- **Location:** app/transcript_import.py:33 (fullmatch).
- **Impact:** Extended SRT timing lines with "X1:.. X2:.. Y1:.. Y2:.." after the end time fail fullmatch, so those cues are skipped silently.
- **Reproduction:** parse_srt("1\n00:00:01,000 --> 00:00:02,000 X1:10 X2:20 Y1:1 Y2:2\nHi\n") returns [].
- **Fix:** Append (?:[ \t].*)? to _TIMING. It stays linear.

### CR-3 (Low, 97)
- **Location:** tests/test_transcript_import.py:23
- **Impact:** "{\an8}" in a non-raw string is "{\x07n8}" (BEL), so the an8 rule is covered only by accident. A real backslash form is removed (checked separately), so this is a test gap, not a code bug.
- **Fix:** Use "{\an8}" or a raw string.

### CR-4 (Info, 95)
- stat/read_bytes raise FileNotFoundError or PermissionError, not ValueError (reproduced). The Markdown title is returned verbatim, e.g. "..\..\evil/name". TASK-024 must catch OSError and pass the title through downloader.safe_name. Nothing to fix in this task.

### CR-5 (Info, 95)
- A UTF-16 BOM file falls through to cp1250 and fails with "no transcript segments found". UTF-16 is outside the acceptance criteria. Optional fix: detect the FF FE / FE FF BOM and decode as utf-16.

## Acceptance check
All acceptance rules are met and tested: API and imports, parse_srt rules, the SRT round trip within 1 ms, Markdown parsing with the end-time formula and round trip, load decoding/title/suffix/ValueError rules, the size check before reading, linear regexes, and no new dependency. Gaps: the CR-1 header-language normalization and the weak an8 test in CR-3.

## Coverage statement
Read the full new module and test file directly (both untracked, and tests/ is gitignored, so git diff shows nothing). Also read exporter.to_markdown/fmt_time, subtitles.to_srt/fmt_srt_time, TranscribeScreen._lang_code and translator.translate_segments/translate. Ran both validation commands and a repro script. Not checked: UI integration (TASK-024), a real 20 MB file, non-Windows paths. The security review is separate. No blocking findings is not proof of correctness.

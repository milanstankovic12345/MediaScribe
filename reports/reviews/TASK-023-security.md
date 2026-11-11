---
task: TASK-023
kind: security
reviewer: security-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/transcript_import.py
  - tests/test_transcript_import.py
  - app/screens/transcribe.py (_lang_code, _run sinks)
  - app/downloader.py (safe_name)
  - app/subtitles.py (embed, burn, iso639_2)
  - app/translator.py (translate)
  - app/exporter.py
not_checked:
  - TASK-024 UI wiring (not written yet)
  - dependency audit (no new dependency)
findings:
  - id: SEC-1
    severity: medium
    title: Markdown Language header returned unvalidated; reaches output file paths once wired (path traversal)
    location: app/transcript_import.py:73-74
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-2
    severity: medium
    title: Quadratic continuation-line concatenation in parse_markdown (CPU DoS from crafted .md)
    location: app/transcript_import.py:79
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-3
    severity: low
    title: 20 MB limit checked by stat() before an unbounded read_bytes() (TOCTOU)
    location: app/transcript_import.py:113-115
    confidence: 70
    status: open
    verified: false
    acceptance_ref: null
  - id: SEC-4
    severity: info
    title: OSError from stat/read escapes with full path instead of ValueError naming the file
    location: app/transcript_import.py:113-115
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### SEC-1 - Unvalidated Markdown language reaches output paths (Medium, confidence 85)
- **Category:** CWE-22 Path Traversal, CWE-20 (OWASP A01/A03:2021).
- **Data path:** `- Language:` value (lines 73-74) -> `Transcript.language` (line 127) -> TASK-024 -> `_lang_code(ORIGINAL, lang)` returns it verbatim (transcribe.py:185) -> `stem = safe_name(title) + "." + lang` (transcribe.py:234, lang not sanitized) -> `out / (stem + ".srt")`, also .md/.pdf/.mp4.
- **Exploit:** a shared `Talk.md` with `- Language: x\..\..\..\escaped`, imported with target Original. Confirmed in-process (mocked IO): load() returns it unchanged; SRT path `C:\Users\someone\Videos\transcripts\Talk.x\..\..\..\escaped.srt` normalises to `C:\Users\someone\escaped.srt`. A colon also yields NTFS ADS names.
- **Impact:** attacker-content files with fixed extensions written or overwritten outside the output folder. Not reachable until TASK-024.
- **Fix:** accept the header language only if in `_KNOWN_CODES` (map sr-Latn->sr, und->empty), else empty. Defence in depth in TASK-024: validate the lang component in `_run`.
- **Test:** `..\..\x` and `en:evil` give language empty; `sr-Latn` gives `sr`.

### SEC-2 - Quadratic concatenation in parse_markdown (Medium, confidence 95)
- **Category:** CWE-407 / CWE-400.
- **Location:** line 79 rebuilds the growing segment string for each continuation line.
- **Measured (in-memory):** one segment + N lines of 50 chars: 20k lines (1 MB) 1.9 s, 40k (2 MB) 13 s, 80k (4 MB) 56 s. A 20 MB file under the limit takes tens of minutes; worker not cancellable.
- **Fix:** keep a list of parts per segment and join once after the loop.
- **Test:** 80k continuation lines parse in under 1 s.

### SEC-3 - Size check not bound to the read (Low, confidence 70)
- **Category:** CWE-367 / CWE-400. A file growing between stat() and read_bytes() is read unbounded. Fix: open in binary mode, `read(MAX_BYTES + 1)`, reject if longer.

### SEC-4 - Raw OSError (Info, confidence 80)
- Missing, locked, or directory paths raise FileNotFoundError/PermissionError with the full path. Wrap in ValueError naming the file only.

## Checked with no finding
- ReDoS: `_TIMING`, `_TAG`, `_BRACES`, `_MD_SEG` have no nested quantifiers. 2M unclosed tags and 5M unclosed braces: 0.22 s. 400k-line SRT cue: 0.13 s.
- Numeric captures bounded; no huge-int conversion.
- Title is not a path here; existing sinks use `downloader.safe_name` (transcribe.py:217, 234).
- Decode fallback errors name the file only.
- Language reaches ffmpeg only via `iso639_2` in an argv list (no shell) and the translator only via dict lookups; Gemini does not get it.
- No network, subprocess, eval or pickle in the module.

## Coverage statement
Inspected the full new module, the test names, and the downstream sinks in transcribe.py, subtitles.py, exporter.py, translator.py and downloader.safe_name. Traversal and timing were confirmed with in-memory Python runs (`.venv`, Path.stat/read_bytes mocked, no files written). References: OWASP Top 10 baseline, input validation. Not reviewed: TASK-024 wiring, Gemini internals, dependencies. This does not establish that the module is secure; it records what was checked.

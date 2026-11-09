---
task: TASK-002
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: block
scope_checked:
  - app/subtitles.py
  - tests/test_subtitles.py
  - app/transcriber.py (Segment, imports)
  - app/exporter.py (write_markdown)
not_checked:
  - Rendering of .srt output in real players
findings:
  - id: CR-1
    severity: high
    title: to_cues chops words into 1-4 char fragments when text is short for the segment duration
    location: app/subtitles.py:70-72
    confidence: 98
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: high
    title: max_dur not enforced; cues up to the full segment length are produced
    location: app/subtitles.py:69-79
    confidence: 98
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: medium
    title: Tests miss short-text/long-duration cases
    location: tests/test_subtitles.py:11-23
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: low
    title: _wrap does not bound line width to ~42 chars
    location: app/subtitles.py:48-57
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-5
    severity: low
    title: Dead and misleading code in _split_point
    location: app/subtitles.py:24-33
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-6
    severity: low
    title: Segment with end < start yields cue with end before start
    location: app/subtitles.py:68-79
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-7
    severity: info
    title: tests/ is git-ignored, new test file will not be committed
    location: .gitignore:14
    confidence: 99
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - Words chopped into fragments (High, 98)
- **Location:** `app/subtitles.py:70-72`, plus the hard cut at line 33.
- **Impact:** `limit = floor(len(text)*max_dur/dur*0.95)` drops to a few chars when there is little text for the duration, and `_split_point` then cuts mid-word. Whisper often gives such segments ("Thank you.", "[Music]", slow speech). The output is unreadable.
- **Reproduction (run):** `Segment(0,12,"Thank you.")` gives "Than", "k", "you.". `Segment(0,30,"Hello world foo")` gives "He","ll","o","wo","rl","d","fo","o". `Segment(0,29,"[Music]")` gives 7 one-char cues.
- **Fix:** Split by text only (`_chunks(text, max_chars)`), with extra splits only at word boundaries and never below one word. Enforce duration by clamping (CR-2).

### CR-2 - max_dur not enforced (High, 98)
- **Location:** `app/subtitles.py:69-79`. Related to the task criterion that cues are each <= 6 s.
- **Impact:** (1) `limit` bottoms out at 1, and a lone char still gets `dur/total`. (2) `total` excludes the spaces stripped at cuts, so `len(text)/total` can exceed 1/0.95. A sweep of 3000 random segments (0.5-30 s, 1-40 words) gave 77 violations, for example a 27.4 s cue "h", a 6.07 s cue from a 60-char/20 s segment, and a 6.7 s cue "gi". The 20 s/200-char acceptance input passes only by construction.
- **Reproduction:** `to_cues([Segment(0,16.91,"j")])` returns `[Segment(0.0,16.91,"j")]`.
- **Fix:** `end = min(end, start + max_dur)`. Keep the next cue at its proportional start. Times stay monotonic and non-overlapping, with gaps.

### CR-3 - Missing tests (Medium, 90)
- **Impact:** All CR-1 and CR-2 inputs pass the current suite. max_dur is checked on one even 200-char input only.
- **Fix:** Add whole-word checks (`Segment(0,12,"Thank you.")`), a check for short text over a long duration (`Segment(0,20,"Ok")`), and a small parametrised sweep checking duration, chars, lines and monotonic times.

### CR-4 - Line width not bounded (Low, 95)
- **Impact:** `_wrap` splits at the space nearest the middle without a width check. Text with no spaces (URL, CJK) stays on one line of up to 84 chars. Two lines max is still met.
- **Fix:** Pick the split that minimises the longer line. Hard-split at the width if there are no spaces.

### CR-5 - Dead code in _split_point (Low, 95)
- **Impact:** `i + 1 < len(window) + 1` is always true. Line 32 is unused and line 33 always returns `limit`, so the comment "cut at its end" is wrong. The generator is hard to read.
- **Fix:** Simplify: last punctuation before limit followed by a space or end of text, then `rfind(" ")`, then `limit`.

### CR-6 - Reversed times (Low, 95)
- **Reproduction:** `Segment(5,3,"abc")` gives a cue from 5.000 to 3.000. `dur` is clamped but `seg.end` is still used.
- **Fix:** Use `max(seg.start, seg.end)` as the end, or skip such segments.

### CR-7 - tests/ git-ignored (Info, 99)
- `git check-ignore` matches `.gitignore:14 tests/`, and `git ls-files tests` is empty. This predates the task and is outside its scope; the orchestrator or a human decides.

## Validation re-run (this session)
- `.venv/Scripts/python -m pytest tests/test_subtitles.py -q`: exit 0, 5 passed (matches handoff)
- `.venv/Scripts/python -m pytest -q`: exit 0, 20 passed (matches handoff)
- Inline stdin probe (no files written): CR-1, CR-2 and CR-6 examples plus a 3000-case sweep; 77 max_dur violations, 0 char or line violations.

## Acceptance check
- fmt_srt_time(3725.5): met.
- 20 s/200-char split: met for that input. The general max_dur guarantee fails (CR-2).
- At most 2 lines: met.
- write_srt BOM, numbering, arrows, non-ASCII, parent dirs: met.
- No UI or ffmpeg imports: met (math, pathlib, app.transcriber, which imports only stdlib).

## Coverage statement
Read all of subtitles.py and test_subtitles.py, the Segment dataclass and transcriber imports, and exporter.write_markdown. Ran both validation commands and an inline probe. Not checked: real player rendering, NaN/inf times, performance on huge inputs. Few findings is not proof of correctness.

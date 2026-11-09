---
task: TASK-002
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 2
verdict: approve_with_notes
scope_checked:
  - app/subtitles.py
  - tests/test_subtitles.py
  - reports/handoffs/TASK-002.md (claims)
  - reports/reviews/TASK-002-code.round-1.md (previous findings)
not_checked:
  - Rendering of .srt output in real players
  - NaN/inf segment times
findings:
  - id: CR-1
    severity: high
    title: to_cues chops words into 1-4 char fragments when text is short for the segment duration
    location: app/subtitles.py:19-52
    confidence: 98
    status: fixed
    verified: true
    acceptance_ref: null
  - id: CR-2
    severity: high
    title: max_dur not enforced; cues up to the full segment length are produced
    location: app/subtitles.py:88
    confidence: 98
    status: fixed
    verified: true
    acceptance_ref: null
  - id: CR-3
    severity: medium
    title: Tests miss short-text/long-duration cases
    location: tests/test_subtitles.py:52-97
    confidence: 90
    status: fixed
    verified: true
    acceptance_ref: null
  - id: CR-4
    severity: low
    title: _wrap does not bound line width to ~42 chars
    location: app/subtitles.py:55-64
    confidence: 95
    status: fixed
    verified: true
    acceptance_ref: null
  - id: CR-5
    severity: low
    title: Dead and misleading code in _split_point
    location: app/subtitles.py:19-40
    confidence: 95
    status: fixed
    verified: true
    acceptance_ref: null
  - id: CR-6
    severity: low
    title: Segment with end < start yields cue with end before start
    location: app/subtitles.py:75
    confidence: 95
    status: fixed
    verified: true
    acceptance_ref: null
  - id: CR-7
    severity: info
    title: tests/ is git-ignored, new test file will not be committed (out of scope for this task)
    location: .gitignore:14
    confidence: 99
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-8
    severity: medium
    title: Long segments often end with a tiny orphan cue (one word, under 1 s)
    location: app/subtitles.py:78-81
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### Previous findings (re-verified this session with an inline probe)
- **CR-1 fixed.** `Segment(0,12,"Thank you.")` now gives `["Thank","you."]`, `Segment(0,30,"Hello world foo")` gives whole words, and `Segment(0,29,"[Music]")` gives one cue (0-6 s). In a 20,000-case sweep there were 0 mid-word cuts for words <= max_chars.
- **CR-2 fixed.** `to_cues([Segment(0,16.91,"j")])` now returns `[Segment(0.0,6.0,"j")]`. The 20,000-case sweep (max_dur 3/6/7, max_chars 42/60/84, 0-30 s) found 0 duration violations and 0 monotonicity or overlap violations.
- **CR-3 fixed.** The new tests cover short text, tiny text, reversed times, wrapping and a seeded sweep. They fail against the round-1 logic by construction (whole-word and max_dur asserts).
- **CR-4 fixed.** Space-less text is now hard-split at 42 (`"x"*84` gives 42+42), and the split minimises the longer line. Residual (info only): when text has very long tokens, a line can still reach about 57 chars (`"a "+"x"*82` gives an 82-char second line). Normal prose stays at 42 or less, and the 2-line maximum always holds.
- **CR-5 fixed.** `_split_point` was rewritten. It has no dead branches, and every return value is >= 1, so `_chunks` always makes progress for max_chars >= 1.
- **CR-6 fixed.** `Segment(5,3,"abc")` now gives `Segment(5.0,5,"abc")`.
- **CR-7 info / out of scope.** `git check-ignore -v tests/test_subtitles.py` still matches `.gitignore:14 tests/`. The orchestrator or a human decides.

### CR-8 - Tiny orphan cue at the end of long segments (Medium, confidence 95)
- **Location:** `app/subtitles.py:78-81` (`limit = ceil(len(text)/pieces)`) together with `_split_point` returning cuts <= limit.
- **Impact:** `limit` is the exact average chunk length. Word-boundary cuts always land at or below it, so the chunks come out slightly short and the leftover becomes an extra chunk of one or a few words. Its proportional share is a fraction of a second, so the viewer sees the last word(s) of a long Whisper segment flash on screen. This hits the main path: splitting long segments is the reason the task exists.
- **Reproduction (run):** The acceptance input (`Segment(5,25, word00..word27 + "word")`) gives 5 cues of 4.9, 4.9, 4.9, 4.9 and **0.41 s** ("word"). For realistic English, `Segment(0,25,"so what we are going to do today ... compare them with what")` ends with a cue of 24.25-25.0 containing just "what". In a sweep of 5,000 prose segments (25-70 words, 8-30 s), **2,461 (49%)** contained a cue shorter than 1 s.
- **Recommended fix:** In `to_cues`, after `_chunks`, merge a short last chunk into the previous one when `len(prev)+1+len(last) <= max_chars` (for example when it is shorter than `limit//3`). The existing `min(end, start+max_dur)` clamp keeps the duration bound. Another option is to give `_split_point` some slack above the target (for example `limit*1.2`, still capped at max_chars). Add a test asserting that no cue is shorter than about 1 s for the 20 s/200-char input.

## Validation re-run (this session)
- `.venv/Scripts/python -m pytest tests/test_subtitles.py -q`: exit 0, 14 passed (matches handoff)
- `.venv/Scripts/python -m pytest -q`: exit 0, 29 passed (matches handoff)
- Inline stdin probes (no files written): all round-1 repro inputs, a 20,000-case random sweep over max_chars/max_dur, a line-width distribution, and a 5,000-case prose sweep for short cues.

## Acceptance check
- fmt_srt_time(3725.5) == "01:02:05,500": met.
- 20 s/200-char split: each cue <= 6 s and <= 84 chars, monotonic, non-overlapping, first start = 5.0 and last end = 25.0: met (but see CR-8).
- At most 2 lines: met (0 violations in the sweep).
- write_srt BOM, numbering, arrows, non-ASCII, parent dirs: met (unchanged, test passes).
- No UI or ffmpeg imports: met (math, pathlib, app.transcriber).

## Questions (below confidence threshold, not defects)
- On sparse segments the design splits words into separate cues ("Thank" for 5.45 s, then "you."), where one cue clamped to 6 s might read better. This is a design choice. It is not a defect under the spec.
- `max_chars <= 0` would loop forever in `_chunks` (`_split_point` returns 0). It is an invalid argument and no caller passes it.

## Coverage statement
Read all of app/subtitles.py and tests/test_subtitles.py, the handoff and the round-1 review. Ran both validation commands and the inline probes listed above. Not checked: rendering in real players, NaN/inf times, performance on very large inputs, and integration with callers (none exist yet). Few findings does not prove the code is correct.

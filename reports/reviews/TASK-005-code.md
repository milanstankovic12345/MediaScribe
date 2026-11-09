---
task: TASK-005
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - tests/test_e2e_subtitles.py
  - app/subtitles.py (embed, burn, to_cues, write_srt)
  - tasks/TASK-005-add-opt-in-ffmpeg-smoke-test-for-subtitle-embed-.md
  - reports/handoffs/TASK-005.md
  - .gitignore
not_checked:
  - Rendered pixel content of burned subtitles (glyph correctness for non-ASCII)
  - Behaviour on ffmpeg builds without libass or libx264
  - Non-Windows platforms
findings:
  - id: CR-1
    severity: low
    title: Burn test does not prove subtitles were actually rendered into the frames
    location: tests/test_e2e_subtitles.py:53
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: info
    title: tests/ is gitignored, so the new test is never committed
    location: .gitignore:14
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - Burn test does not prove subtitles were actually rendered into the frames (Low, confidence 90)

- **Location:** `tests/test_e2e_subtitles.py:53-61`
- **Impact:** The test checks that there is a video stream, that there is no subtitle stream, and that the file fully decodes. A regression in `burn()` that drops the `subtitles=` filter, for example by replacing `-vf subtitles=subs.srt` with a plain re-encode, would still pass. The acceptance criterion only asks for "a playable output with no subtitle stream", so the criterion is met. This finding is about the stated objective ("prove burn() produces valid videos") being weaker than the test name suggests.
- **Reproduction:** Change `burn()` so it builds `cmd` without the `-vf subtitles=subs.srt` pair. Run `YT_TOOL_E2E=1 pytest tests/test_e2e_subtitles.py`. The burn test still passes. This follows from the assertions; I did not mutate production code.
- **Recommended fix (optional):** Extract one frame at t=0.5 s from both `clip` and `out`, for example `ffmpeg -ss 0.5 -i X -frames:v 1 -f rawvideo -pix_fmt gray -`, and assert that the bytes differ, or that the bottom band differs. This keeps the test cheap and catches a filter that silently does nothing.

### CR-2 - tests/ is gitignored, so the new test is never committed (Info, confidence 95)

- **Location:** `.gitignore:14` (`tests/` sits under "Dev-only, kept locally")
- **Impact:** `git check-ignore -v tests/test_e2e_subtitles.py` matches this rule, and `git ls-files tests` is empty. This was a pre-existing project decision and is not caused by this task. The handoff does not mention it, so the file only exists locally.
- **Reproduction:** `git check-ignore -v tests/test_e2e_subtitles.py` prints `.gitignore:14:tests/`.
- **Recommended fix:** None for this task. The orchestrator or owner can decide whether tests should be tracked.

## Validation re-run (this session)

| Command | Exit | Result |
|---|---|---|
| `.venv/Scripts/python -m pytest tests/test_e2e_subtitles.py -q -rs` | 0 | 2 skipped, reason "set YT_TOOL_E2E=1 and put ffmpeg/ffprobe on PATH to run" |
| `.venv/Scripts/python -m pytest -q` | 0 | 51 passed, 2 skipped in 0.82s (matches the handoff) |
| `YT_TOOL_E2E=1 .venv/Scripts/python -m pytest tests/test_e2e_subtitles.py -q` | 0 | 2 passed in 0.52s against real ffmpeg 9.0.2 (Gyan full build) |

The results match the handoff claims. `pytest.ini` was not created. That is correct, because `skipif` needs no marker registration.

## Acceptance check

- Skip guard: `pytestmark` requires `YT_TOOL_E2E == "1"`, `which("ffmpeg")` and `which("ffprobe")`, and the default suite skips. Met.
- E2E content: a 3 s lavfi testsrc+sine clip, a 2-cue SRT with Serbian diacritics built through `to_cues`/`write_srt` (len 2 asserted), `embed()` with ffprobe showing a `subtitle` stream, and `burn()` with a `video` stream, no `subtitle` stream and a full null decode. Met.
- All artifacts are under `tmp_path`. `burn()` also uses its own `TemporaryDirectory`, which is production code. Met.
- No production code was modified. Scope stays within `files_allowed`.

## Coverage statement

Inspected: the full test file, `app/subtitles.py` (`embed`, `burn` and the cue/SRT helpers the test uses), the task file, the handoff and `.gitignore`. Ran the default and opt-in validation with real ffmpeg on Windows. Not checked: whether non-ASCII glyphs render correctly in the burned frames, behaviour on ffmpeg builds without libass or libx264 (the test would fail with CalledProcessError or RuntimeError instead of skipping, which is acceptable for an opt-in smoke test), and non-Windows platforms. Finding no defects is not proof of correctness.

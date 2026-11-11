---
task: TASK-022
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/exporter.py
  - app/settings.py
  - app/screens/transcribe.py
  - app/screens/base.py
  - app/ui.py
  - app/transcriber.py
  - tests/test_core.py
  - tests/test_transcribe_screen.py
  - tests/test_gemini.py
  - reports/handoffs/TASK-022.md
  - reports/metrics/events.jsonl
not_checked:
  - Visual layout of the Translated document checkbox in the Translate to row (no window opened)
  - Real Whisper/NLLB/Gemini/ffmpeg runs
findings:
  - id: CR-1
    severity: low
    title: Tests do not cover sub_doc with Embed/Burn, translate-once, or collect_cfg sub_doc
    location: tests/test_transcribe_screen.py:377
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: info
    title: Header says Translated from even when Gemini skipped translation for a same-language target
    location: app/screens/transcribe.py:237
    confidence: 85
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: Handoff risk claims the open questions were not answered, but events.jsonl records that the user accepted them
    location: reports/handoffs/TASK-022.md:18
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
---

## Summary

The change does what the acceptance criteria ask. `translated_from` is a trailing keyword in `to_markdown`, `write_markdown` and `write_pdf`. The `sub_doc` default exists and `settings.load` merges it, so `self.cfg["sub_doc"]` cannot raise KeyError (`app/ui.py:23` uses `settings.load()`). The checkbox, `_args` 12th element, `_validate` message, `collect_cfg` key and `_run(..., sub_doc=())` all match the spec. The `_args` positions match `_run` positions through `Screen._worker` (`base.py:178`). Documents are written after `_prog(0.85)` and before `write_srt`, so `saved[-1]` stays the SRT or the video. The original-transcript calls keep 4 positional arguments. No dependency was added. Nothing actionable blocks.

## Validation (re-run by reviewer)

- `.venv/Scripts/python -m pytest tests/test_core.py tests/test_transcribe_screen.py -q`: exit 0, 83 passed (matches the handoff)
- `.venv/Scripts/python -m pytest -q`: exit 0, 205 passed, 2 skipped (matches the handoff)

## Extra checks run by reviewer

- Byte-identity: loaded the de8a82e `exporter.py` from `git show` in memory and compared `to_markdown` old against new for three transcripts (normal, empty segments, language None). It was identical with no keyword, with `translated_from=None` and with `""`. With `"en"` the output has `- Language: de\n- Translated from: en\n\n` as specified.
- Ran `_run` with stub I/O in a temp dir: target Serbian (Latin), `sub_doc=(".md", ".pdf")`, Embed and then Burn. Saved order was `[.sr-Latn.md, .sr-Latn.pdf, .sr-Latn.srt, .sr-Latn.mp4 / .burned.mp4]`. The returned path was the video. Progress was monotonic. The real Markdown file had the expected header. A non-ASCII title (`Café: Talk`) was sanitized through `safe_name`.
- `_validate` short-circuit: `not (md or pdf) and sub_doc_var.get()` does not read `sub_doc_var` when MD or PDF is ticked. The `tests/test_gemini.py:230` stub has no `sub_doc_var` and still passes. The new check comes last, so existing message order is unchanged. Transcribe mode returns before it.

## Findings

### CR-1: Tests do not cover sub_doc with Embed/Burn, translate-once, or collect_cfg sub_doc (Low, confidence 95)

- **Location:** `tests/test_transcribe_screen.py:377` (translated-document tests)
- **Impact:** The code is correct today. I confirmed it with the reviewer run above. But there is no regression guard for three acceptance points: the `[md, pdf, srt, video]` order where `saved[-1]` is the embedded/burned video, "translates once", and `collect_cfg` writing `"sub_doc"`. A later reorder, such as moving the document write after `embed`, would change the Open folder target and no test would fail.
- **Reproduction:** Move the `if sub_doc:` block below the `if sub_video == EMBED` branch in `_run`. All 205 tests still pass, but `_run(..., EMBED, sub_doc=(".md",))` now returns the `.md` as the Open folder path.
- **Recommended fix:** Parametrize `test_run_sub_doc_writes_translated_md_pdf` over `[SRT_ONLY, EMBED, BURN]` and assert that `last` is the srt/mp4/burned.mp4. Count `translate_segments` calls (`== 1`). Add a small `collect_cfg` test on a stub, or note it as covered manually.

### CR-2: Header says "Translated from" even when Gemini skipped translation for a same-language target (Info, confidence 85)

- **Location:** `app/screens/transcribe.py:237`
- **Impact:** This is cosmetic. With the Gemini engine and a source equal to the target (for example, detected `de` and target German), `translator.translate` skips Gemini. The document still gets `- Language: de` / `- Translated from: de`. This follows the acceptance rule exactly ("translated_from when target is not Original"), so it is not a defect against the spec.
- **Reproduction:** German audio, engine Gemini, target German, Translated document ticked. The `.de.md` header has `Translated from: de`.
- **Recommended fix (optional):** Pass `None` when `lang.split("-")[0] == t.language`. That would also drop the line for `sr` to `sr-Latn` transliteration, which is arguably still a "translation", so a human should decide.

### CR-3: Handoff risk claims the open questions were not answered (Info, confidence 95)

- **Location:** `reports/handoffs/TASK-022.md` (risks)
- **Impact:** This is a documentation inaccuracy only. `reports/metrics/events.jsonl:262` records `draft -> ready` with the reason "open questions answered: user accepted all recommended answers". The implementation matches those answers.
- **Recommended fix:** None needed for the code. The orchestrator can disregard that risk line.

## Questions

- None blocking. A manual visual check is still needed: does the Translate to row (label, 170 px menu, Video label, 180 px menu, checkbox) fit the default window width without clipping?

## Coverage statement

Inspected: the full diff of `app/exporter.py`, `app/settings.py` and `app/screens/transcribe.py` against de8a82e, plus the whole of `transcribe.py`. Also read `base.py` (`_start`/`_worker` arg passing), the `app/ui.py` cfg source, `Transcript`/`Segment` in `transcriber.py`, the new and existing tests in `tests/test_core.py` and `tests/test_transcribe_screen.py`, and the Gemini `_validate` stub in `tests/test_gemini.py`. I ignored the 1-line TASK-021 change (`text=self.button_text`) as out of scope.
Ran: both validation commands, an in-memory old-versus-new Markdown byte comparison, and a stubbed `_run` with Embed/Burn plus `sub_doc` in a temp dir.
Not checked: the visual layout of the new checkbox (no window opened), real Whisper/NLLB/Gemini/ffmpeg behaviour, PDF glyph rendering for Cyrillic targets beyond the existing font fallback, and docs (deferred to TASK-025). Absence of findings is not proof of correctness.

---
task: TASK-013
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/translator.py (full file; diff vs fb6fe58 lines 166-185)
  - tests/test_translator.py (full file; working tree, gitignored so absent from git diff)
  - app/gemini.py:168-196 (translate_segments fallback contract, read only)
  - app/screens/transcribe.py:138-142,194-201 (caller of translator.translate)
not_checked:
  - Real Gemini API and real NLLB model behaviour (no network or model by design)
  - Multi-chunk fallback through the real gemini.translate_segments (tests only exercise a monkeypatched fake; I probed a 2-segment single-chunk case manually)
  - UI behaviour of the Transcribe screen (not visually verified)
findings:
  - id: CR-1
    severity: info
    title: Same-language shortcut drops Gemini script conversion for Serbian Latin-script transcripts with the Serbian (Cyrillic) target
    location: app/translator.py:172
    confidence: 80
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: info
    title: Progress callback is not invoked on the same-language shortcut
    location: app/translator.py:172
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: One log line per failed chunk is only tested with a single chunk
    location: tests/test_translator.py:189-197
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
---

## Summary

The change matches the task's decisions exactly. `translate` computes `tgt` and `src` once and adds `(src is not None and src == tgt)` to the local-dispatch condition (`app/translator.py:170-173`). That reuses the existing `src == tgt` branch of `translate_segments` (lines 135-138), so the logic is not duplicated. The lambda fallback is replaced with an inner `fallback` (lines 176-182). For an unsupported source it logs "Local translation does not support '<src_iso>'; keeping the original text for this part." and returns the chunk unchanged. Otherwise it calls `translate_segments(chunk, src_iso, target_label, None, log)` as before. `translate_segments` is untouched, there are no new imports or dependencies, module state is untouched, and nothing secret is logged (only `src_iso`).

The returned chunk works with `gemini.translate_segments` (`app/gemini.py:193-194`): it zips the chunk with the returned `part` and takes `p.text`, so the original texts are kept and timestamps come from `segments`. The fallback runs once per failed chunk, which gives one log line per chunk.

Acceptance criteria against the code and tests:
- Same language (en/English, hr/Croatian, sr/Serbian (Cyrillic)): `test_gemini_same_language_skips_api` patches both `_fetch` and `_get_model` to raise, asserts unchanged text and timestamps, and asserts there were no Gemini calls. Met.
- Serbian (Latin): `test_gemini_same_language_serbian_latin` gives [(1,2,"Ljubav"),(2,3,"Zdravo")] with no Gemini call and no model load. Met.
- Different languages: `test_gemini_different_language_calls_api` covers en->German and sr->Croatian and asserts (segs, label, "key", "m"). Met.
- Unsupported source fallback (ja, None): text is kept, there is one log line containing the source code and "original text", nothing is raised, and no NLLB is loaded. Met. See CR-3 for the test gap.
- Supported source fallback: `test_gemini_fallback_supported_source_uses_nllb` goes through the `fake` NLLB and gets "HELLO WORLD". Met.
- Local engine unchanged: `test_unsupported_source_raises` passes, and so does the full suite including tests/test_gemini.py. Met.

## Validation (re-run by reviewer)

- `.venv/Scripts/python -m pytest tests/test_translator.py -q` exited 0 with 21 passed. This matches the handoff.
- `.venv/Scripts/python -m pytest -q` exited 0 with 157 passed and 2 skipped. This matches the handoff.
- Manual probe with a fake `gemini.translate_segments` that always calls the fallback:
  - translate([x, y], "ja", "Bosnian", GEMINI) returned the segments unchanged with exactly one log line.
  - translate([x], "bs", "Bosnian", GEMINI) returned the input unchanged with no fallback.
  - translate([x], None, ORIGINAL, GEMINI) returned the input unchanged.

## Findings

### CR-1 - Same-language shortcut drops Gemini script conversion for Serbian Latin-script transcripts (Info, confidence 80)

- **Location:** `app/translator.py:172`
- **Impact:** Whisper's `sr` output is often in Latin script, or mixes scripts. Before this change, the Gemini engine with the "Serbian (Cyrillic)" target sent that text to Gemini, which returned Cyrillic. Now WHISPER_TO_NLLB["sr"] == TARGETS["Serbian (Cyrillic)"] == "srp_Cyrl", so the text comes back unchanged and the subtitle file can stay in Latin script even though the user chose Cyrillic. The task's acceptance criterion requires exactly this behaviour, and the local engine already behaves this way, so this is not a defect of the task. I am recording it for the product owner.
- **Reproduction:** translate([Segment(0,1,"Zdravo")], "sr", "Serbian (Cyrillic)", GEMINI_ENGINE, key) returns "Zdravo" and does not produce the Cyrillic form.
- **Recommended fix:** None for this task. If Latin-to-Cyrillic output matters, a later task could add a lat_to_cyr transliteration for that target. That also covers the local engine.

### CR-2 - Progress callback not invoked on the same-language shortcut (Info, confidence 90)

- **Location:** `app/translator.py:172` (the `translate_segments` same-language branch at lines 135-138 never calls `cb`)
- **Impact:** None in practice. TranscribeScreen._run sets _prog(0.85) right after translation (app/screens/transcribe.py:200). The progress bar jumps instead of reaching the end of the translation sub-range, which is the same as local-engine behaviour today.
- **Reproduction:** Call translate(segs, "en", "English", GEMINI_ENGINE, "k", cb=progress.append). Afterwards progress == [].
- **Recommended fix:** Optional. Call cb(1.0) in the same-language branch of translate_segments if consistent progress is wanted. That change is outside this task's "do not change translate_segments" decision.

### CR-3 - Per-chunk log line only tested with one chunk (Info, confidence 90)

- **Location:** `tests/test_translator.py:189-197`
- **Impact:** The fake gemini.translate_segments calls fallback once, so "one line per failed chunk" is only checked for N=1. The code is correct by construction (the log is inside fallback, which is called once per chunk), so the risk is low.
- **Reproduction:** Not applicable. This is a coverage gap, not a failing behaviour.
- **Recommended fix:** Optional. Have the fake split segments into two chunks, call fallback for each, and assert len(logs) == 2.

## Questions

None.

## Coverage statement

I inspected the full diff of app/translator.py against fb6fe58 and the whole current tests/test_translator.py. That file is gitignored (.gitignore:14), so I read it directly. I also read the fallback contract in app/gemini.py:168-196 and the caller in app/screens/transcribe.py. I re-ran both validation commands and a manual edge-case probe. I did not run the real Gemini API, real NLLB or the real multi-chunk gemini path, and I did not check the UI visually. app/gemini.py changes belong to TASK-012 and were not reviewed here. A review with no blocking findings does not prove the code is correct.
